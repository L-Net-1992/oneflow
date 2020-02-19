#ifndef ONEFLOW_CORE_VM_CONTROL_VPU_H_
#define ONEFLOW_CORE_VM_CONTROL_VPU_H_

#include "oneflow/core/vm/vpu.h"
#include "oneflow/core/vm/vm_instruction.msg.h"

namespace oneflow {

class VpuScheduler;
class VmInstructionMsg;

class ControlVpu final {
 public:
  ControlVpu() = default;
  ~ControlVpu() = default;

  ObjectMsgPtr<VmInstructionMsg> NewMirroredObjectSymbol(uint64_t symbol, bool is_remote,
                                                         int64_t parallel_num) const;
  ObjectMsgPtr<VmInstructionMsg> DeleteMirroredObjectSymbol(
      const LogicalObjectId& logical_object_id) const;

  void Run(VpuScheduler* scheduler, VmInstructionMsg* vm_instr_msg) const;
};

static const VmStreamTypeId kControlVmStreamTypeId = 0;

}  // namespace oneflow

#endif  // ONEFLOW_CORE_VM_CONTROL_VPU_H_
