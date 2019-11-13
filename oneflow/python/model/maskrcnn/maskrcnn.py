# must import get cfg before importing oneflow
from config import get_default_cfgs

import os
import numpy as np
import argparse
import oneflow as flow
import oneflow.core.data.data_pb2 as data_util

from datetime import datetime
from backbone import Backbone
from rpn import RPNHead, RPNLoss, RPNProposal
from box_head import BoxHead
from mask_head import MaskHead
from blob_watcher import save_blob_watched, blob_watched, diff_blob_watched


parser = argparse.ArgumentParser()
parser.add_argument(
    "-c", "--config_file", default=None, type=str, help="yaml config file"
)
parser.add_argument("-bz", "--batch_size", type=int, default=1, required=False)
parser.add_argument(
    "-load", "--model_load_dir", type=str, default="", required=False
)
parser.add_argument(
    "-g", "--gpu_num_per_node", type=int, default=1, required=False
)
parser.add_argument(
    "-d",
    "--debug",
    type=bool,
    default=True,
    required=False,
    help="debug with random data generated by numpy",
)
parser.add_argument(
    "-rpn", "--rpn_only", default=False, action="store_true", required=False
)
parser.add_argument(
    "-md", "--mock_dataset", default=False, action="store_true", required=False
)
parser.add_argument(
    "-mp",
    "--mock_dataset_path",
    type=str,
    default="/tmp/shared_with_zwx/mock_data_600x1000_b2.pkl",
    required=False,
)
parser.add_argument(
    "-eval", "--eval", default=False, action="store_true", required=False
)
parser.add_argument(
    "-td",
    "--train_with_real_dataset",
    default=False,
    action="store_true",
    required=False,
)
parser.add_argument(
    "-cp", "--ctrl_port", type=int, default=19765, required=False
)
parser.add_argument(
    "-save",
    "--model_save_dir",
    type=str,
    default="./model_save-{}".format(
        str(datetime.now().strftime("%Y-%m-%d--%H-%M-%S"))
    ),
    required=False,
)
parser.add_argument(
    "-v", "--verbose", default=False, action="store_true", required=False
)
parser.add_argument("-i", "--iter_num", type=int, default=10, required=False)
parser.add_argument(
    "-lr", "--primary_lr", type=float, default=0.0002, required=False
)
parser.add_argument(
    "-slr", "--secondary_lr", type=float, default=0.0004, required=False
)
parser.add_argument(
    "-fake", "--fake_image_path", type=str, default="", required=False
)
parser.add_argument(
    "-anno",
    "--annotation_file",
    type=str,
    default="instances_val2017.json",
    required=False,
)
parser.add_argument(
    "-imgd", "--image_dir", type=str, default="val2017", required=False
)
terminal_args = parser.parse_args()


debug_data = None

if terminal_args.mock_dataset:
    from mock_data import MockData

    debug_data = MockData(terminal_args.mock_dataset_path, 64)


def get_numpy_placeholders():
    import numpy as np

    (N, H, W, C) = (2, 64, 64, 3)
    R = 50
    G = 12
    return {
        "images": np.random.randn(N, H, W, C).astype(np.float32),
        "image_sizes": np.random.randn(N, 2).astype(np.int32),
        "gt_boxes": np.random.randn(N, R, 4).astype(np.float32),
        "gt_segms": np.random.randn(N, G, 28, 28).astype(np.int8),
        "gt_labels": np.random.randn(N, G).astype(np.int32),
        "rpn_proposals": np.random.randn(2000, 4).astype(np.float32),
        "detections": np.random.randn(2000, 4).astype(np.float32),
        "detection0": np.random.randn(1000, 4).astype(np.float32),
        "detection1": np.random.randn(1000, 4).astype(np.float32),
        "fpn_feature_map1": np.random.randn(2, 256, 104, 152).astype(
            np.float32
        ),
        "fpn_feature_map2": np.random.randn(2, 256, 52, 76).astype(np.float32),
        "fpn_feature_map3": np.random.randn(2, 256, 26, 38).astype(np.float32),
        "fpn_feature_map4": np.random.randn(2, 256, 13, 19).astype(np.float32),
    }


placeholders = get_numpy_placeholders()


def maskrcnn_train(images, image_sizes, gt_boxes, gt_segms, gt_labels):
    r"""Mask-RCNN
    Args:
    images: (N, H, W, C)
    image_sizes: (N, 2)
    gt_boxes: (N, R, 4), dynamic
    gt_segms: (N, G, 28, 28), dynamic
    gt_labels: (N, G), dynamic
    """
    assert images.is_dynamic is True
    assert images.shape[3] == 3
    assert image_sizes.is_dynamic is False
    assert gt_boxes.num_of_lod_levels == 2
    # if it is mask target projected, num_of_lod_levels is 0
    if gt_segms.num_of_lod_levels == 0:
        assert gt_segms.is_dynamic is True
    else:
        assert gt_segms.num_of_lod_levels == 2
    assert gt_labels.num_of_lod_levels == 2
    cfg = get_default_cfgs()
    if terminal_args.config_file is not None:
        cfg.merge_from_file(terminal_args.config_file)
        print("merged config from {}".format(terminal_args.config_file))
    cfg.freeze()
    if terminal_args.verbose:
        print(cfg)

    backbone = Backbone(cfg)
    rpn_head = RPNHead(cfg)
    rpn_loss = RPNLoss(cfg)
    rpn_proposal = RPNProposal(cfg)
    box_head = BoxHead(cfg)
    mask_head = MaskHead(cfg)

    image_size_list = [
        flow.squeeze(
            flow.local_gather(image_sizes, flow.constant(i, dtype=flow.int32)),
            [0],
        )
        for i in range(image_sizes.shape[0])
    ]
    gt_boxes_list = flow.piece_slice(
        gt_boxes, cfg.TRAINING_CONF.IMG_PER_GPU, name="piece_gt_boxes"
    )
    gt_labels_list = flow.piece_slice(
        gt_labels, cfg.TRAINING_CONF.IMG_PER_GPU, name="piece_slice_gt_labels"
    )
    gt_segms_list = None
    if gt_segms.num_of_lod_levels == 2:
        gt_segms_list = flow.piece_slice(
            gt_segms, cfg.TRAINING_CONF.IMG_PER_GPU, name="piece_slice_gt_segms"
        )
    else:
        gt_segms_list = gt_segms
    anchors = []
    for i in range(cfg.DECODER.FPN_LAYERS):
        anchors.append(
            flow.detection.anchor_generate(
                images=images,
                feature_map_stride=cfg.DECODER.FEATURE_MAP_STRIDE * pow(2, i),
                aspect_ratios=cfg.DECODER.ASPECT_RATIOS,
                anchor_scales=cfg.DECODER.ANCHOR_SCALES * pow(2, i),
            )
        )

    # Backbone
    # CHECK_POINT: fpn features
    # with flow.watch_scope(blob_watcher=blob_watched, diff_blob_watcher=diff_blob_watched):
    features = backbone.build(flow.transpose(images, perm=[0, 3, 1, 2]))

    # RPN
    # with flow.watch_scope(blob_watcher=blob_watched, diff_blob_watcher=diff_blob_watched):
    cls_logit_list, bbox_pred_list = rpn_head.build(features)
    rpn_bbox_loss, rpn_objectness_loss = rpn_loss.build(
        anchors, image_size_list, gt_boxes_list, bbox_pred_list, cls_logit_list
    )
    if terminal_args.rpn_only:
        return rpn_bbox_loss, rpn_objectness_loss

    proposals = rpn_proposal.build(
        anchors, cls_logit_list, bbox_pred_list, image_size_list, gt_boxes_list
    )

    # with flow.watch_scope(blob_watcher=blob_watched, diff_blob_watcher=diff_blob_watched), flow.watch_scope(blob_watcher=MakeWatcherCallback("forward"), diff_blob_watcher=MakeWatcherCallback("backward")):
    # Box Head
    box_loss, cls_loss, pos_proposal_list, pos_gt_indices_list = box_head.build_train(
        proposals, gt_boxes_list, gt_labels_list, features
    )

    # Mask Head
    mask_loss = mask_head.build_train(
        pos_proposal_list,
        pos_gt_indices_list,
        gt_segms_list,
        gt_labels_list,
        features,
    )

    return rpn_bbox_loss, rpn_objectness_loss, box_loss, cls_loss, mask_loss


def MakeWatcherCallback(prompt):
    def Callback(blob, blob_def):
        if prompt == "forward":
            return
        print(
            "%s, lbn: %s, min: %s, max: %s"
            % (prompt, blob_def.logical_blob_name, blob.min(), blob.max())
        )

    return Callback


def maskrcnn_eval_box_head(images, image_sizes):
    cfg = get_default_cfgs()
    if terminal_args.config_file is not None:
        cfg.merge_from_file(terminal_args.config_file)
    cfg.freeze()
    print(cfg)
    backbone = Backbone(cfg)
    rpn_head = RPNHead(cfg)
    rpn_proposal = RPNProposal(cfg)
    box_head = BoxHead(cfg)

    image_size_list = [
        flow.squeeze(
            flow.local_gather(image_sizes, flow.constant(i, dtype=flow.int32)),
            [0],
        )
        for i in range(image_sizes.shape[0])
    ]
    anchors = []
    for i in range(cfg.DECODER.FPN_LAYERS):
        anchors.append(
            flow.detection.anchor_generate(
                images=flow.transpose(images, perm=[0, 2, 3, 1]),
                feature_map_stride=cfg.DECODER.FEATURE_MAP_STRIDE * pow(2, i),
                aspect_ratios=cfg.DECODER.ASPECT_RATIOS,
                anchor_scales=cfg.DECODER.ANCHOR_SCALES * pow(2, i),
            )
        )

    # Backbone
    features = backbone.build(images)

    # RPN
    cls_logit_list, bbox_pred_list = rpn_head.build(features)
    proposals = rpn_proposal.build(
        anchors, cls_logit_list, bbox_pred_list, image_size_list, None
    )

    # Box Head
    cls_probs, box_regressions = box_head.build_eval(proposals, features)

    return (
        tuple(proposals) + tuple(features) + (cls_probs,) + (box_regressions,)
    )


if terminal_args.mock_dataset:

    @flow.function
    def mock_train(
        images=debug_data.blob_def("images"),
        image_sizes=debug_data.blob_def("image_size"),
        gt_boxes=debug_data.blob_def("gt_bbox"),
        gt_segms=debug_data.blob_def("segm_mask_targets"),
        gt_labels=debug_data.blob_def("gt_labels"),
    ):
        flow.config.train.primary_lr(terminal_args.primary_lr)
        print("primary_lr:", terminal_args.primary_lr)
        flow.config.train.model_update_conf(dict(naive_conf={}))
        # TODO: distribute map only support remote blob for now, so identity is required here
        image_sizes = flow.identity(image_sizes)
        outputs = maskrcnn_train(
            flow.transpose(images, perm=[0, 2, 3, 1]),
            image_sizes,
            gt_boxes,
            gt_segms,
            gt_labels,
        )
        for loss in outputs:
            flow.losses.add_loss(loss)
        return outputs


def input_blob_def(bn):
    return flow.input_blob_def(
        placeholders[bn].shape, dtype=flow.float32, is_dynamic=True
    )


if terminal_args.eval:
    from eval.bounding_box import BoxList
    from eval.box_head_inference import PostProcessor
    from eval.mask_head_inference import MaskPostProcessor
    from eval.coco import COCODataset
    from eval.coco_eval import do_coco_evaluation

    @flow.function
    def maskrcnn_box_head_eval_job(
        images=flow.input_blob_def(
            (2, 3, 416, 608), dtype=flow.float, is_dynamic=True
        ),
        image_sizes=flow.input_blob_def(
            (2, 2), dtype=flow.int32, is_dynamic=False
        ),
    ):
        return maskrcnn_eval_box_head(images, image_sizes)

    @flow.function
    def maskrcnn_mask_head_eval_job(
        detection0=input_blob_def("detection0"),
        detection1=input_blob_def("detection1"),
        fpn_fm1=input_blob_def("fpn_feature_map1"),
        fpn_fm2=input_blob_def("fpn_feature_map2"),
        fpn_fm3=input_blob_def("fpn_feature_map3"),
        fpn_fm4=input_blob_def("fpn_feature_map4"),
    ):
        cfg = get_default_cfgs()
        mask_head = MaskHead(cfg)
        mask_logits = mask_head.build_eval(
            [detection0, detection1], [fpn_fm1, fpn_fm2, fpn_fm3, fpn_fm4]
        )
        mask_prob = flow.math.sigmoid(mask_logits)
        return mask_prob


if terminal_args.train_with_real_dataset:

    def make_data_loader(
        batch_size,
        batch_cache_size=3,
        dataset_dir="/dataset/mscoco_2017",
        annotation_file="annotations/instances_train2017.json",
        image_dir="train2017",
        random_seed=123456,
        shuffle=False,
        group_by_aspect_ratio=True,
    ):
        coco = flow.data.COCODataset(
            dataset_dir,
            annotation_file,
            image_dir,
            random_seed,
            shuffle,
            group_by_aspect_ratio,
        )
        data_loader = flow.data.DataLoader(coco, batch_size, batch_cache_size)
        data_loader.add_blob(
            "image",
            data_util.DataSourceCase.kImage,
            shape=(1344, 800, 3),
            dtype=flow.float,
            is_dynamic=True,
        )
        data_loader.add_blob(
            "image_size",
            data_util.DataSourceCase.kImageSize,
            shape=(2,),
            dtype=flow.int32,
        )
        data_loader.add_blob(
            "gt_bbox",
            data_util.DataSourceCase.kObjectBoundingBox,
            shape=(64, 4),
            dtype=flow.float,
            variable_length_axes=(0,),
            is_dynamic=True,
        )
        data_loader.add_blob(
            "gt_labels",
            data_util.DataSourceCase.kObjectLabel,
            shape=(64,),
            dtype=flow.int32,
            variable_length_axes=(0,),
            is_dynamic=True,
        )
        data_loader.add_blob(
            "gt_segm_poly",
            data_util.DataSourceCase.kObjectSegmentation,
            shape=(64, 2, 256, 2),
            dtype=flow.double,
            variable_length_axes=(0, 1, 2),
            is_dynamic=True,
        )
        data_loader.add_blob(
            "gt_segm",
            data_util.DataSourceCase.kObjectSegmentationAlignedMask,
            shape=(64, 1344, 800),
            dtype=flow.int8,
            variable_length_axes=(0,),
            is_dynamic=True,
        )
        data_loader.add_transform(flow.data.TargetResizeTransform(800, 1333))
        data_loader.add_transform(
            flow.data.ImageNormalizeByChannel((102.9801, 115.9465, 122.7717))
        )
        data_loader.add_transform(flow.data.ImageAlign(32))
        data_loader.add_transform(
            flow.data.SegmentationPolygonListToAlignedMask()
        )
        data_loader.init()
        return data_loader

    def init_conf():
        flow.config.cudnn_conv_heuristic_search_algo(True)
        flow.config.cudnn_conv_use_deterministic_algo_only(False)
        flow.config.train.primary_lr(terminal_args.primary_lr)
        flow.config.train.secondary_lr(terminal_args.secondary_lr)
        flow.config.train.weight_l2(0.0001)
        flow.config.train.model_update_conf(dict(momentum_conf={"beta": 0.9}))
        # flow.config.train.model_update_conf(dict(naive_conf={}))

    def init_train_func(fake_image):
        if fake_image:

            @flow.function
            def train(
                image_blob=flow.input_blob_def(
                    shape=(2, 800, 1344, 3), dtype=flow.float32, is_dynamic=True
                )
            ):
                init_conf()
                data_loader = make_data_loader(
                    batch_size=terminal_args.batch_size,
                    batch_cache_size=3,
                    annotation_file=terminal_args.annotation_file,
                    image_dir=terminal_args.image_dir,
                )
                outputs = maskrcnn_train(
                    image_blob,
                    data_loader("image_size"),
                    data_loader("gt_bbox"),
                    data_loader("gt_segm"),
                    data_loader("gt_labels"),
                )
                for loss in outputs:
                    flow.losses.add_loss(loss)
                return outputs

            return train
        else:

            @flow.function
            def train():
                init_conf()
                data_loader = make_data_loader(
                    batch_size=terminal_args.batch_size,
                    batch_cache_size=3,
                    annotation_file=terminal_args.annotation_file,
                    image_dir=terminal_args.image_dir,
                )
                outputs = maskrcnn_train(
                    data_loader("image"),
                    data_loader("image_size"),
                    data_loader("gt_bbox"),
                    data_loader("gt_segm"),
                    data_loader("gt_labels"),
                )
                for loss in outputs:
                    flow.losses.add_loss(loss)
                return outputs

            return train


if __name__ == "__main__":
    flow.config.gpu_device_num(terminal_args.gpu_num_per_node)
    flow.config.ctrl_port(terminal_args.ctrl_port)
    flow.config.default_data_type(flow.float)
    fake_image_list = []
    if terminal_args.fake_image_path:
        file_list = os.listdir(terminal_args.fake_image_path)
        fake_image_list = [
            np.load(os.path.join(terminal_args.fake_image_path, f))
            for f in file_list
        ]

    train_func = init_train_func(len(fake_image_list) > 0)

    check_point = flow.train.CheckPoint()
    if not terminal_args.model_load_dir:
        check_point.init()
    else:
        check_point.load(terminal_args.model_load_dir)

    if terminal_args.debug:
        if terminal_args.eval:
            import numpy as np

            images = np.load(
                "/tmp/shared_with_jxf/maskrcnn_eval_input_data_small/images.npy"
            )
            image_sizes = np.load(
                "/tmp/shared_with_jxf/maskrcnn_eval_input_data_small/image_sizes.npy"
            )
            image_num = image_sizes.shape[0]

            results = maskrcnn_box_head_eval_job(images, image_sizes).get()
            cls_probs = results[-2]
            box_regressions = results[-1]
            fpn_feature_map = []
            for i in range(4):
                fpn_feature_map.append(results[image_num + i].ndarray())

            boxes = []
            for proposal, img_size in zip(results[:image_num], image_sizes):
                bbox = BoxList(
                    proposal.ndarray(), (img_size[1], img_size[0]), mode="xyxy"
                )
                boxes.append(bbox)
            postprocessor = PostProcessor()
            results = postprocessor.forward(
                (cls_probs.ndarray(), box_regressions.ndarray()), boxes
            )

            detections = []
            for result in results:
                detections.append(result.bbox)
            mask_prob = maskrcnn_mask_head_eval_job(
                detections[0],
                detections[1],
                fpn_feature_map[0],
                fpn_feature_map[1],
                fpn_feature_map[2],
                fpn_feature_map[3],
            ).get()

            mask_postprocessor = MaskPostProcessor()
            predictions = mask_postprocessor.forward(
                mask_prob.ndarray(), results
            )

            ann_file = "/dataset/mscoco_2017/annotations/sample_2_instances_val2017.json"
            dataset = COCODataset(ann_file)
            do_coco_evaluation(
                dataset,
                predictions,
                box_only=False,
                output_folder="./output",
                iou_types=["bbox", "segm"],
                expected_results=(),
                expected_results_sigma_tol=4,
            )
        elif terminal_args.mock_dataset:
            if terminal_args.rpn_only:
                print(
                    "{:>8} {:>16} {:>16}".format(
                        "iter", "rpn_bbox_loss", "rpn_obj_loss"
                    )
                )
            else:
                print(
                    "{:>8} {:>16} {:>16} {:>16} {:>16} {:>16}".format(
                        "iter",
                        "loss_rpn_box_reg",
                        "loss_objectness",
                        "loss_box_reg",
                        "loss_classifier",
                        "loss_mask",
                    )
                )
            for i in range(terminal_args.iter_num):

                def save_model():
                    return
                    if not os.path.exists(terminal_args.model_save_dir):
                        os.makedirs(terminal_args.model_save_dir)
                    model_dst = os.path.join(
                        terminal_args.model_save_dir, "iter-" + str(i)
                    )
                    print("saving models to {}".format(model_dst))
                    check_point.save(model_dst)

                if i == 0:
                    save_model()

                train_loss = mock_train(
                    debug_data.blob("images"),
                    debug_data.blob("image_size"),
                    debug_data.blob("gt_bbox"),
                    debug_data.blob("segm_mask_targets"),
                    debug_data.blob("gt_labels"),
                ).get()
                fmt_str = "{:>8} " + "{:>16.10f} " * len(train_loss)
                print_loss = [i]
                for loss in train_loss:
                    print_loss.append(loss.mean())
                print(fmt_str.format(*print_loss))
                save_blob_watched(i)

                if (i + 1) % 10 == 0:
                    save_model()

        elif terminal_args.train_with_real_dataset:
            print(
                "{:>8} {:>16} {:>16} {:>16} {:>16} {:>16}".format(
                    "iter",
                    "loss_rpn_box_reg",
                    "loss_objectness",
                    "loss_box_reg",
                    "loss_classifier",
                    "loss_mask",
                )
            )
            for i in range(terminal_args.iter_num):
                if i < len(fake_image_list):
                    train_loss = train_func(fake_image_list[i]).get()
                else:
                    train_loss = train_func().get()

                fmt_str = "{:>8} " + "{:>16.10f} " * len(train_loss)
                print_loss = [i]
                for loss in train_loss:
                    print_loss.append(loss.mean())
                print(fmt_str.format(*print_loss))

                save_blob_watched(i)
