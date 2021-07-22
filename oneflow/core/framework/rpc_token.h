/*
Copyright 2020 The OneFlow Authors. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/
#ifndef ONEFLOW_CORE_FRAMEWORK_RPC_TOKEN_H_
#define ONEFLOW_CORE_FRAMEWORK_RPC_TOKEN_H_

#include "oneflow/core/common/type_traits.h"
#include "oneflow/core/common/maybe.h"

namespace oneflow {

enum RpcTokenType {
  // Begin
  kDataRpcTokenType = 0, // e.g. for tensor data transportation
  kOpTensorMetaRpcTokenType, // e.g. for tensor shape synchronizing or checking
  kCmdRpcTokenType, // e.g. for rank_group or thread checking
  kExtendedRpcTokenType, // for compatibility
  // End
  kRpcTokenTypeSize,
};

static_assert(kRpcTokenTypeSize <= (1 << 2), "");

enum RankGroupRpcCmd {
  // Begin
	kRankGroupRpcCmdInvalid = 0,
	kRankGroupRpcCmdSyncSymbolParallelDesc,
	kRankGroupRpcCmdSyncSymbolParallelDistribution,
	kRankGroupRpcCmdSyncSymbolConsistentTensorMeta,
  // End
	kSizeOfRankGroupRpcCmd
};

class RpcToken;

template<>
struct IsScalarType<RpcToken> final {
  static const bool value = true;
};

class RpcToken final {
 public:
  RpcToken(const RpcToken&) = default;
  RpcToken(RpcToken&) = default;
  ~RpcToken() = default;

	static RpcToken NewDataRpcToken();
	static Maybe<RpcToken> NewOpTensorMetaRpcToken();
	static Maybe<RpcToken> NewCmdRpcToken(RankGroupRpcCmd cmd);

	static size_t MaxNumberOfThreadConsistentUId() { return (1 << 3); }

  // Getters
  int64_t src_rank() const { return src_rank_; }
  int64_t dst_rank() const { return dst_rank_; }
  RpcTokenType type() const { return static_cast<RpcTokenType>(type_); }
  Maybe<int64_t> thread_consistent_unique_id() const;
  Maybe<int64_t> rank_group_id() const;
	Maybe<RankGroupRpcCmd> cmd() const;

  // Setters
	Maybe<void> set_src_rank(int64_t src_rank);
	Maybe<void> set_dst_rank(int64_t dst_rank);
	Maybe<void> set_data_seq_id(int64_t data_seq_id);

  operator uint64_t() const;
  RpcToken& operator++();

 private:
	explicit RpcToken(RpcTokenType type): type_(type) {}

	static RpcToken NewOpTensorMetaRpcToken(int32_t thread_consistent_unique_id, int32_t rank_group_id);
	static RpcToken NewCmdRpcToken(RankGroupRpcCmd cmd, int32_t thread_consistent_unique_id, int32_t rank_group_id);

  uint16_t src_rank_;
  uint16_t dst_rank_;
  uint32_t type_:2; // RpcTokenType
	union {
		uint32_t data_seq_id_:30; // used by kDataRpcTokenType only
		struct {
			uint32_t thread_consistent_unique_id_:3;
			uint32_t rank_group_id_:3;
			union {
				uint32_t meta_seq_id_:24; // used by kOpTensorMetaRpcTokenType only
				struct {
			  	uint8_t cmd_; // RankGroupRpcCmd
					uint16_t cmd_seq_id_; // used by kCmdRpcTokenType only
				};
			};
		};
	};
};
static_assert(sizeof(RpcToken) == sizeof(uint64_t), "");

}  // namespace oneflow

#endif  // ONEFLOW_CORE_FRAMEWORK_RPC_TOKEN_H_