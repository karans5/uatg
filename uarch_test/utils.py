import ruamel
from ruamel.yaml import YAML
import os
import glob
import uarch_test
from uarch_test.log import logger
from yapsy.PluginManager import PluginManager

global _path
_path = os.path.dirname(uarch_test.__file__)


def list_of_modules():
    modules = os.listdir(_path + '/modules/')
    return modules + ['all']


def clean_cli_params(config_file, module, gen_test, val_test, gen_cvg):
    error = (False, '')
    available_modules = list_of_modules()
    try:
        module = module.replace(' ', ',')
        module = module.replace(', ', ',')
        module = module.replace(' ,', ',')
        module = list(set(module.split(",")))
        module.remove('')
        module.sort()
    except ValueError as e:
        pass
    for i in module:
        if i not in available_modules:
            error = (True, 'Module {0} is not supported/unavailable.'.format(i))
    if 'all' in module:
        module = ['all']

    if (gen_test or val_test) and config_file is None:
        error = (True, "Can not generate/validate with config_file path "
                 "missing")
    if (gen_cvg) and not gen_test:
        error = (True,
                 'Cannot generate covergroups without generating the tests')

    return module, error


def load_yaml(foo):
    yaml = YAML(typ="rt")
    yaml.default_flow_style = False
    yaml.allow_unicode = True
    try:
        with open(foo, "r") as file:
            return yaml.load(file)
    except ruamel.yaml.constructor.DuplicateKeyError as msg:
        logger.error('error: {0}'.format(msg))


def create_plugins(plugins_path):
    files = os.listdir(plugins_path)
    for i in files:
        if ('.py' in i) and (not i.startswith('.')):
            module_name = i[0:-3]
            f = open(plugins_path + '/' + module_name + '.yapsy-plugin', "w")
            f.write("[Core]\nName=" + module_name + "\nModule=" + module_name)
            f.close()


def generate_test_list(asm_dir, uarch_dir, test_list):
    """
      updates the test_list.yaml file of rivercore with the location of the
      tests generated by test_generator as well the directory to dump the logs
    """
    asm_test_list = glob.glob(asm_dir + '/**/*[!_template].S')
    env_dir = os.path.join(uarch_dir, 'env/')
    target_dir = asm_dir + '/../'

    for test in asm_test_list:
        logger.debug("Current test is {0}".format(test))
        base_key = os.path.basename(test)[:-2]
        test_list[base_key] = {}
        test_list[base_key]['generator'] = 'uarch_test'
        test_list[base_key]['work_dir'] = asm_dir + '/' + base_key
        test_list[base_key]['isa'] = 'rv64imafdc'
        test_list[base_key]['march'] = 'rv64imafdc'
        test_list[base_key]['mabi'] = 'lp64'
        test_list[base_key]['cc'] = 'riscv64-unknown-elf-gcc'
        test_list[base_key][
            'cc_args'] = ' -mcmodel=medany -static -std=gnu99 -O2 -fno-common -fno-builtin-printf -fvisibility=hidden '
        test_list[base_key][
            'linker_args'] = '-static -nostdlib -nostartfiles -lm -lgcc -T'
        test_list[base_key]['linker_file'] = target_dir + '/' + 'link.ld'
        test_list[base_key][
            'asm_file'] = asm_dir + '/' + base_key + '/' + base_key + '.S'
        test_list[base_key]['include'] = [env_dir, target_dir]
        test_list[base_key]['compile_macros'] = ['XLEN=64']
        test_list[base_key]['extra_compile'] = []
        test_list[base_key]['result'] = 'Unavailable'

    return test_list


def create_linker(target_dir):
    out = '''OUTPUT_ARCH( "riscv" )
ENTRY(rvtest_entry_point)

SECTIONS
{
  . = 0x80000000;
  .text.init : { *(.text.init) }
  . = ALIGN(0x1000);
  .tohost : { *(.tohost) }
  . = ALIGN(0x1000);
  .text : { *(.text) }
  . = ALIGN(0x1000);
  .data : { *(.data) }
  .data.string : { *(.data.string)}
  .bss : { *(.bss) }
  _end = .;
} 
'''

    with open(target_dir + '/' + "link.ld", "w") as outfile:
        outfile.write(out)


def create_model_test_h(target_dir):
    out = '''#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                            \
        .align 8; .global tohost; tohost: .dword 0;                     \
        .align 8; .global fromhost; fromhost: .dword 0;                 \
        .popsection;                                                    \
        .align 8; .global begin_regstate; begin_regstate:               \
        .word 128;                                                      \
        .align 8; .global end_regstate; end_regstate:                   \
        .word 4;

//RV_COMPLIANCE_HALT
#define RVMODEL_HALT                                              \
shakti_end:                                                             \
      li gp, 1;                                                         \
      sw gp, tohost, t5;                                                \
      fence.i;                                                           \
      li t6, 0x20000;                                                   \
      la t5, begin_signature;                                           \
      sw t5, 0(t6);                                                     \
      la t5, end_signature;                                             \
      sw t5, 8(t6);                                                     \
      sw t5, 12(t6);  

#define RVMODEL_BOOT

//RV_COMPLIANCE_DATA_BEGIN
#define RVMODEL_DATA_BEGIN                                              \
  RVMODEL_DATA_SECTION                                                        \
  .align 4; .global begin_signature; begin_signature:

//RV_COMPLIANCE_DATA_END
#define RVMODEL_DATA_END                                                      \
        .align 4; .global end_signature; end_signature:  

//RVTEST_IO_INIT
#define RVMODEL_IO_INIT
//RVTEST_IO_WRITE_STR
#define RVMODEL_IO_WRITE_STR(_R, _STR)
//RVTEST_IO_CHECK
#define RVMODEL_IO_CHECK()
//RVTEST_IO_ASSERT_GPR_EQ
#define RVMODEL_IO_ASSERT_GPR_EQ(_S, _R, _I)
//RVTEST_IO_ASSERT_SFPR_EQ
#define RVMODEL_IO_ASSERT_SFPR_EQ(_F, _R, _I)
//RVTEST_IO_ASSERT_DFPR_EQ
#define RVMODEL_IO_ASSERT_DFPR_EQ(_D, _R, _I)

#define RVMODEL_SET_MSW_INT \
 li t1, 1;                         \
 li t2, 0x2000000;                 \
 sw t1, 0(t2);

#define RVMODEL_CLEAR_MSW_INT     \
 li t2, 0x2000000;                 \
 sw x0, 0(t2);

#define RVMODEL_CLEAR_MTIMER_INT

#define RVMODEL_CLEAR_MEXT_INT
#endif // _COMPLIANCE_MODEL_H'''

    with open(target_dir + '/' + 'model_test.h', 'w') as outfile:
        outfile.write(out)
