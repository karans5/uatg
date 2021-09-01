import os
import glob
from shutil import rmtree
from getpass import getuser
from datetime import datetime
import ruamel.yaml as yaml
import utg
from utg.utils import create_plugins, generate_test_list
from utg.utils import create_linker, create_model_test_h
from utg.utils import join_yaml_reports, generate_sv_components
from utg.utils import list_of_modules
from yapsy.PluginManager import PluginManager
from utg.log import logger

# from utg.__init__ import __version__
# from utg.utils import load_yaml


def generate_tests(work_dir,
                   linker_dir,
                   modules,
                   config_dict,
                   test_list,
                   modules_dir,
                   verbose='info'):
    """
    specify the location where the python test files are located for a
    particular module with the folder following / , Then load the plugins from
    the plugin directory and create the asm test files in a new directory.
    eg. module_class  = branch_predictor's object
    """
    uarch_dir = os.path.dirname(utg.__file__)

    if work_dir:
        pass
    else:
        work_dir = os.path.abspath((os.path.join(uarch_dir, '../work/')))

    os.makedirs(work_dir, exist_ok=True)
    logger.level(verbose)

    logger.info(f'utg dir is {uarch_dir}')
    logger.info(f'work_dir is {work_dir}')

    inp_yaml = config_dict
    isa = inp_yaml['ISA']
    if modules == ['all']:
        logger.debug(f'Checking {modules_dir} for modules')
        modules = list_of_modules(modules_dir, verbose)
    logger.debug(f'The modules are {modules}')

    test_list_dict = {}
    logger.info('****** Generating Tests ******')
    for module in modules:
        module_dir = os.path.join(modules_dir, module)
        work_tests_dir = os.path.join(work_dir, module)
        try:
            module_params = config_dict[module]
        except KeyError:
            # logger.critical("The {0} module is not in the dut config_file",
            # format(module))
            module_params = {}
        logger.debug(f'Directory for {module} is {module_dir}')
        logger.info(f'Starting plugin Creation for {module}')
        create_plugins(plugins_path=module_dir)
        logger.info(f'Created plugins for {module}')
        username = getuser()
        time = ((str(datetime.now())).split("."))[0]

        asm_header = f'## Licensing information can be found at LICENSE.' \
                     f'incore\n## Test generated by user - {username} at ' \
                     f'{time}\n\n#include \"model_test.h\" \n#include \"arch_' \
                     f'test.h\"\nRVTEST_ISA(\"{isa}\")\n\n.section .text.' \
                     f'init\n.globl rvtest_entry_point\nrvtest_entry_point:' \
                     f'\nRVMODEL_BOOT\nRVTEST_CODE_BEGIN\n\n'
        asm_footer = '\nRVTEST_CODE_END\nRVMODEL_HALT\n\nRVTEST_DATA_BEGIN\n' \
                     '.align 4\nrvtest_data:\n.word ' \
                     '0xbabecafe\nRVTEST_DATA_END\n\nRVMODEL_DATA_BEGIN' \
                     '\nRVMODEL_DATA_END\n '

        manager = PluginManager()
        manager.setPluginPlaces([module_dir])
        # plugins are stored in module_dir
        manager.collectPlugins()

        # check if prior test files are present and remove them. create new dir.
        if (os.path.isdir(work_tests_dir)) and \
                os.path.exists(work_tests_dir):
            rmtree(work_tests_dir)
        print("making work tests dir")
        os.mkdir(work_tests_dir)

        logger.debug(f'Generating assembly tests for {module}')

        # Loop around and find the plugins and writes the contents from the
        # plugins into an asm file
        for plugin in manager.getAllPlugins():
            _check = plugin.plugin_object.execute(module_params)
            _name = (str(plugin.plugin_object).split(".", 1))
            _test_name = ((_name[1].split(" ", 1))[0])
            if _check:
                _asm_body = plugin.plugin_object.generate_asm()
                _asm = asm_header + _asm_body + asm_footer
                os.mkdir(os.path.join(work_tests_dir, _test_name))
                with open(
                        os.path.join(work_tests_dir, _test_name,
                                     _test_name + '.S'), "w") as f:
                    f.write(_asm)
                logger.debug(f'Generating test for {_test_name}')
            else:
                logger.critical(f'Skipped {_test_name}')
        logger.debug(f'Finished Generating Assembly Tests for {module}')
        if test_list:
            logger.info(f'Creating test_list for the {module}')
            test_list_dict.update(
                generate_test_list(work_tests_dir, uarch_dir, test_list_dict))

    logger.info('****** Finished Generating Tests ******')

    if linker_dir and os.path.isfile(os.path.join(linker_dir, 'link.ld')):
        logger.debug('Using user specified linker')
    else:
        create_linker(target_dir=work_dir)
        logger.debug(f'Creating a linker file at {work_dir}')

    if linker_dir and os.path.isfile(os.path.join(linker_dir, 'model_test.h')):
        logger.debug('Using user specified model_test file')
    else:
        create_model_test_h(target_dir=work_dir)
        logger.debug(f'Creating Model_test.h file at {work_dir}')
    if test_list:
        logger.info('Test List was generated by utg. You can find it in '
                    'the work dir ')
    else:
        logger.info('Test list will not be generated by utg')
    if test_list:
        with open(work_dir + '/' + 'test_list.yaml', 'w') as outfile:
            yaml.dump(test_list_dict, outfile)


def generate_sv(work_dir,
                config_dict,
                modules,
                modules_dir,
                alias_dict,
                verbose='info'):
    """specify the location where the python test files are located for a
    particular module with the folder following / , Then load the plugins from
    the plugin directory and create the cover-groups (System Verilog) for the
    test files in a new directory.
    """
    logger.level(verbose)
    uarch_dir = os.path.dirname(utg.__file__)

    if work_dir:
        pass
    else:
        work_dir = os.path.abspath((os.path.join(uarch_dir, '../work/')))

    if modules == ['all']:
        logger.debug(f'Checking {modules_dir} for modules')
        modules = list_of_modules(modules_dir, verbose)

    inp_yaml = config_dict
    logger.info('****** Generating Covergroups ******')

    sv_dir = os.path.join(work_dir, 'sv_top')
    os.makedirs(sv_dir, exist_ok=True)

    # generate the tbtop and interface files
    generate_sv_components(sv_dir, alias_dict)
    logger.debug("Generated tbtop, defines and interface files")
    sv_file = os.path.join(sv_dir, 'coverpoints.sv')

    if os.path.isfile(sv_file):
        logger.debug("Removing Existing coverpoints SV file")
        os.remove(sv_file)

    for module in modules:
        logger.debug(f'Generating CoverPoints for {module}')

        module_dir = os.path.join(modules_dir, module)

        try:
            module_params = inp_yaml[module]
        except KeyError:
            module_params = {}

        manager = PluginManager()
        manager.setPluginPlaces([module_dir])
        manager.collectPlugins()

        for plugin in manager.getAllPlugins():
            _check = plugin.plugin_object.execute(module_params)
            _name = (str(plugin.plugin_object).split(".", 1))
            _test_name = ((_name[1].split(" ", 1))[0])
            if _check:
                try:
                    _sv = plugin.plugin_object.generate_covergroups(alias_dict)
                    # TODO: Check what the name of the SV file should be
                    # TODO: Include the creation of TbTop and Interface SV files
                    with open(sv_file, "a") as f:
                        logger.info(
                            f'Generating coverpoints SV file for {_test_name}')
                        f.write(_sv)

                except AttributeError:
                    logger.warn(
                        f'Skipping coverpoint generation for {_test_name} as '
                        f'there is no gen_covergroup method ')
                    pass

            else:
                logger.critical(f'Skipped {_test_name} as this test is not '
                                f'created for the current DUT configuration ')

        logger.debug(f'Finished Generating Coverpoints for {module}')
    logger.info('****** Finished Generating Covergroups ******')


def validate_tests(modules, config_dict, work_dir, modules_dir, verbose='info'):
    """
       Parses the log returned from the DUT for finding if the tests
       were successful
    """

    logger.level(verbose)
    uarch_dir = os.path.dirname(utg.__file__)
    inp_yaml = config_dict

    logger.info('****** Validating Test results, Minimal log checking ******')

    if modules == ['all']:
        logger.debug(f'Checking {modules_dir} for modules')
        modules = list_of_modules(modules_dir)
        # del modules[-1]
        # Needed if list_of_modules returns 'all' along with other modules
    if work_dir:
        pass
    else:
        work_dir = os.path.abspath((os.path.join(uarch_dir, '../work/')))

    _pass_ct = 0
    _fail_ct = 0
    _tot_ct = 1

    for module in modules:
        module_dir = os.path.join(modules_dir, module)
        # module_tests_dir = os.path.join(module_dir, 'tests')
        work_tests_dir = os.path.join(work_dir, module)
        reports_dir = os.path.join(work_dir, 'reports', module)
        os.makedirs(reports_dir, exist_ok=True)

        try:
            module_params = inp_yaml[module]
        except KeyError:
            # logger.critical("The {0} module is not "
            #                 "in the dut config_file",format(module))
            module_params = {}

        manager = PluginManager()
        manager.setPluginPlaces([module_dir])
        manager.collectPlugins()

        logger.debug(f'Minimal Log Checking for {module}')

        for plugin in manager.getAllPlugins():
            _name = (str(plugin.plugin_object).split(".", 1))
            _test_name = ((_name[1].split(" ", 1))[0])
            _check = plugin.plugin_object.execute(module_params)
            if _check:
                try:
                    _result = plugin.plugin_object.check_log(
                        log_file_path=os.path.join(work_tests_dir, _test_name,
                                                   'log'),
                        reports_dir=reports_dir)
                    if _result:
                        logger.info(f'{_tot_ct}. Minimal test: {_test_name} '
                                    f'has passed.')
                        _pass_ct += 1
                        _tot_ct += 1
                    else:
                        logger.critical(f"{_tot_ct}. Minimal test: "
                                        f"{_test_name} has failed.")
                        _fail_ct += 1
                        _tot_ct += 1
                except FileNotFoundError:
                    logger.error(f'Log for {_test_name} not found. Run the '
                                 f'test on DUT and generate log or check '
                                 f'the path.')
            else:
                logger.warn(f'No asm generated for {_test_name}. Skipping')
        logger.debug(f'Minimal log Checking for {module} complete')

    logger.info("Minimal Verification Results")
    logger.info("=" * 28)
    logger.info(f"Total Tests : {_tot_ct - 1}")

    if _tot_ct - 1:
        logger.info(f"Tests Passed : {_pass_ct} - "
                    f"[{_pass_ct // (_tot_ct - 1)} %]")
        logger.warn(f"Tests Failed : {_fail_ct} - "
                    f"[{100 * _fail_ct // (_tot_ct - 1)} %]")
    else:
        logger.warn("No tests were created")

    logger.info('****** Finished Validating Test results ******')
    join_yaml_reports(work_dir)
    logger.info('Joined Yaml reports')


def clean_dirs(work_dir, modules_dir, verbose='info'):
    """
    This function cleans unwanted files. Presently it removes __pycache__,
    tests/ directory inside modules and yapsy plugins.
    """
    logger.level(verbose)
    uarch_dir = os.path.dirname(utg.__file__)
    if work_dir:
        pass
    else:
        work_dir = os.path.abspath((os.path.join(uarch_dir, '../work/')))

    module_dir = os.path.join(work_dir, '**')
    # module_tests_dir = os.path.join(module_dir, 'tests')

    logger.info('****** Cleaning ******')
    logger.debug(f'work_dir is {module_dir}')
    yapsy_dir = os.path.join(modules_dir, '**/*.yapsy-plugin')
    pycache_dir = os.path.join(modules_dir, '**/__pycache__')
    logger.debug(f'yapsy_dir is {yapsy_dir}')
    logger.debug(f'pycache_dir is {pycache_dir}')
    tf = glob.glob(module_dir)
    pf = glob.glob(pycache_dir) + glob.glob(
        os.path.join(uarch_dir, '__pycache__'))
    yf = glob.glob(yapsy_dir, recursive=True)
    logger.debug(f'removing {tf}, {yf} and {pf}')
    for element in tf + pf:
        if os.path.isdir(element):
            rmtree(element)
        else:
            os.remove(element)

    for element in yf:
        os.remove(element)
    logger.info("Generated Test files/folders removed")
