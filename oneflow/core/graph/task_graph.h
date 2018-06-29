#ifndef ONEFLOW_CORE_GRAPH_TASK_GRAPH_H_
#define ONEFLOW_CORE_GRAPH_TASK_GRAPH_H_

#include "oneflow/core/graph/logical_graph.h"
#include "oneflow/core/job/id_manager.h"
#include "oneflow/core/job/parallel_desc.h"
#include "oneflow/core/operator/operator.h"

namespace oneflow {

class TaskGraph final : public Graph<TaskNode, TaskEdge> {
 public:
  OF_DISALLOW_COPY_AND_MOVE(TaskGraph);
  TaskGraph() = delete;
  ~TaskGraph() = default;

  TaskGraph(std::unique_ptr<const LogicalGraph>&& logical_gph);

  const char* TypeName() const override { return "TaskGraph"; }
  void AddOrderingCtrlEdgeInSameChain();
  void AddMutexCtrlEdgeInSameChain();
  void AddOrderCtrlEdgeBetweenCopyAndMdUpdt();
  void AcyclicTopoForEachNode(std::function<void(TaskNode* node)> handler) const;

#define DECLARE_BLD_SUB_TASK_GRAPH_METHOD(method_name) void method_name BLD_SUB_TSK_GPH_MTHD_ARGS();

  DECLARE_BLD_SUB_TASK_GRAPH_METHOD(BldSubTskGphByBoxing);
  DECLARE_BLD_SUB_TASK_GRAPH_METHOD(BldSubTskGphByOneToOne);
  DECLARE_BLD_SUB_TASK_GRAPH_METHOD(BldSubTskGphBySelectOneSourceToSoleSink);
  DECLARE_BLD_SUB_TASK_GRAPH_METHOD(BldSubTskGphByReduceScatter2ReduceLocalAdd);
  DECLARE_BLD_SUB_TASK_GRAPH_METHOD(BldSubTskGphByReduceScatter2ReduceGlobalAdd);
  DECLARE_BLD_SUB_TASK_GRAPH_METHOD(BldSubTskGphByReduceLocalAdd2ReduceGlobalAdd);
  DECLARE_BLD_SUB_TASK_GRAPH_METHOD(BldSubTskGphByReduceGlobalAdd2ReduceGather);

 private:
  void BuildTaskPath(
      CompTaskNode* src, CompTaskNode* dst,
      std::function<TaskNode**(CompTaskNode* src, int64_t machine_id, int32_t mem_zone_id)>
          MutBufTask,
      bool use_buf_task_node);
  TaskNode* BuildTaskStep(
      TaskNode* cur_node, TaskNode* dst,
      std::function<TaskNode*(int64_t machine_id, int32_t mem_zone_id)> GetBufTask,
      std::function<TaskNode*(int64_t machine_id, int32_t mem_zone_id, TaskNode*)> SetBufTask,
      bool use_buf_task_node);
  TaskNode* AddCopyH2DTaskTo(TaskNode*);
  TaskNode* AddCopyD2HTaskFrom(TaskNode*);
  TaskNode* AddCopyCommNetTaskBetween(TaskNode* src, TaskNode* dst);
  void BuildOutBoxing(const LogicalNode* logical,
                      const std::vector<CompTaskNode*>& sorted_comp_tasks,
                      std::vector<TaskNode*>* sorted_out_box,
                      std::function<int64_t(const TaskNode*)> AllocateCpuThrdId);
  void BuildInBoxing(const LogicalNode* logical,
                     const std::vector<CompTaskNode*>& sorted_comp_tasks,
                     std::vector<TaskNode*>* sorted_in_box,
                     std::function<int64_t(const TaskNode*)> AllocateCpuThrdId);
  void ConnectWithCopyCommNetIfNeed(TaskNode* src, TaskNode* dst);

  void SetAreaIdForNewNodes(const LogicalNode* src_logical, const LogicalNode* dst_logical);
  void CollectAncestorsForEachNode();
  void FindChainsInSameStream();

  std::unique_ptr<const LogicalGraph> logical_gph_;
  std::vector<TaskNode*> ordered_task_nodes_;
};
bool IsBackEdge(TaskNode* src, TaskNode* dst);

}  // namespace oneflow

#endif  // ONEFLOW_CORE_GRAPH_TASK_GRAPH_H_
