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

#ifndef ONEFLOW_USER_KERNELS_RANDINT_KERNEL_H_
#define ONEFLOW_USER_KERNELS_RANDINT_KERNEL_H_

#include "oneflow/core/framework/framework.h"
#include "oneflow/user/kernels/op_kernel_state_wrapper.h"
#include "oneflow/core/common/data_type.h"
#include "oneflow/core/device/device_context.h"
#include "oneflow/core/framework/random_generator.h"
#include "oneflow/core/ndarray/xpu_util.h"
#include "oneflow/core/device/cuda_util.h"
namespace oneflow {
class RandintKernelState : public user_op::OpKernelState {
 public:
  explicit RandintKernelState(const std::shared_ptr<one::Generator>& generator)
      : generator_(generator) {}
  const std::shared_ptr<one::Generator>& generator() const { return generator_; }

 private:
  std::shared_ptr<one::Generator> generator_;
};
}  // namespace oneflow
#endif  // ONEFLOW_USER_KERNELS_RANDINT_KERNEL_H_