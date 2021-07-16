import ruamel
from ruamel.yaml import YAML
import os
import uarch_test
from uarch_test.log import logger
from yapsy.PluginManager import PluginManager

global _path
_path = os.path.dirname(uarch_test.__file__)

def list_of_modules(): 
    modules = os.listdir(_path + '/modules/')
    return modules + ['all']


def clean_cli_params(config_file, work_dir, module, gen_test, val_test):
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

    if work_dir is None:
        work_dir = '/'

    return work_dir, module, error


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


def create_linker(target_dir='target/'):
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

    with open(_path + '/' + target_dir + "link.ld", "w") as outfile:
        outfile.write(out)


def generate_yaml(module='branch_predictor',
                  inp='target/dut_config.yaml',
                  river_path="/",
                  work_dir="bpu/"):
    """
      updates the test_list.yaml file of rivercore with the location of the
      tests generated by test_generator as well the directory to dump the logs
    """
    parent_dir = os.getcwd()
    module_dir = os.path.join(parent_dir, 'modules', module)
    module_tests_dir = os.path.join(module_dir, 'tests')
    target_dir = os.path.join(parent_dir, 'target')
    env_dir = os.path.join(parent_dir, 'env')
    linker_dir = os.path.join(target_dir, 'link.ld')
    inp_yaml = load_yaml(inp)
    module_params = inp_yaml[module]

    manager = PluginManager()
    manager.setPluginPlaces([module_dir])
    manager.collectPlugins()

    _path = river_path + "/mywork/"
    _data = ""
    _generated_tests = 0

    # To-Do -> Create Yaml the proper way. Do not use strings!!

    for plugin in manager.getAllPlugins():
        _check = plugin.plugin_object.execute(module_params)
        _name = (((str(plugin.plugin_object).split(".", 1))[1]).split(" ",
                                                                      1))[0]
        _path_to_tests = os.path.join(module_tests_dir, _name)
        if _check:
            _data += _name + ":\n"
            _data += "  asm_file: " + os.path.join(_path_to_tests,
                                                   _name + '.S') + '\n'
            _data += "  cc: riscv64-unknown-elf-gcc\n"
            _data += "  cc_args: \' -mcmodel=medany -static -std=gnu99 -O2 " \
                     "-fno-common -fno-builtin-printf -fvisibility=hidden \'\n"
            _data += "  compile_macros: [XLEN=64]\n"
            _data += "  extra_compile: []\n"
            _data += "  generator: micro_arch_test_v0.0.1\n"
            _data += "  include: [" + env_dir + ', ' + target_dir + "]\n"
            _data += "  linker_args: -static -nostdlib -nostartfiles" \
                     " -lm -lgcc -T\n"
            _data += "  linker_file: " + linker_dir + "\n"
            _data += "  mabi: lp64\n"
            _data += "  march: rv64imafdc\n"
            _data += "  isa: rv64imafdc\n"
            _data += "  result: Unknown\n"
            _data += "  work_dir: " + _path_to_tests + "\n\n"
            _generated_tests = _generated_tests + 1
        else:
            logger.critical(
                'No test generated for {0}, skipping it in test_list'.format(
                    _name))

    with open(_path + 'test_list.yaml', 'w') as outfile:
        outfile.write(_data)
    return _generated_tests
