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
#ifndef ONEFLOW_CORE_FRAMEWORK_OP_INTERPRETER_BOXING_NAIVE_B2P_BOXING_INTERPRETER_H_
#define ONEFLOW_CORE_FRAMEWORK_OP_INTERPRETER_BOXING_NAIVE_B2P_BOXING_INTERPRETER_H_

#include "oneflow/core/framework/op_interpreter/boxing/eager_boxing_interpreter.h"

namespace oneflow {

class NaiveB2PBoxingInterpreter final : public EagerBoxingInterpreter {
 public:
  OF_DISALLOW_COPY_AND_MOVE(NaiveB2PBoxingInterpreter);
  NaiveB2PBoxingInterpreter() = default;
  ~NaiveB2PBoxingInterpreter() override = default;

  Maybe<void> Interpret(const one::TensorTuple& inputs, one::TensorTuple* outputs,
                        Symbol<cfg::ParallelDistribution> in_parallel_distribution,
                        Symbol<cfg::ParallelDistribution> out_parallel_distribution,
                        Symbol<ParallelDesc> in_parallel_desc,
                        Symbol<ParallelDesc> out_parallel_desc) const override;
};

}  // namespace oneflow

#endif  // ONEFLOW_CORE_FRAMEWORK_OP_INTERPRETER_BOXING_NAIVE_B2P_BOXING_INTERPRETER_H_
