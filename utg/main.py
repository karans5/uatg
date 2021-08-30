# See LICENSE.incore for details
"""Console script for utg."""

import click
from configparser import ConfigParser
from utg.log import logger
from utg.test_generator import generate_tests, clean_dirs, validate_tests, \
    generate_sv
from utg.__init__ import __version__
from utg.utils import list_of_modules, info, load_yaml


@click.group()
@click.version_option(version=__version__)
def cli():
    """RISC-V Micro-Architectural Test Generator"""

# -----------------


@click.version_option(version=__version__)
@click.option('--module_dir',
              '-md',
              multiple=False,
              required=False,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Absolute Path to the directory containing the python files"
                   " which generate the assembly tests. "
                   "Required Parameter")
@click.option('--work_dir',
              '-wd',
              multiple=False,
              required=True,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Path to the working directory where generated files will be"
                   " stored.")
@click.option('--verbose',
              '-v',
              default='info',
              help='Set verbose level for debugging',
              type=click.Choice(['info', 'error', 'debug'],
                                case_sensitive=False))
@cli.command()
def clean(module_dir, work_dir, verbose):
    """
    Removes ASM, SV and other generated files from the work directory, and
    removes .yapsy plugins from module directory.\n
    Requires: -wd, --work_dir\n
    Optional: -md, --module_dir; -v, --verbose
    """
    logger.level(verbose)
    info(__version__)
    logger.debug('Invoking clean_dirs')
    clean_dirs(work_dir=work_dir, modules_dir=module_dir, verbose=verbose)


# -------------------------


@click.version_option(version=__version__)
@click.option('--alias_file',
              '-af',
              multiple=False,
              required=False,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Path to the aliasing file containing containing BSV alias "
                   "names.")
@click.option('--dut_config',
              '-dc',
              multiple=False,
              required=True,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Path to the yaml file containing DUT configuration. "
                   "Needed to generate/validate tests")
@click.option('--module_dir',
              '-md',
              multiple=False,
              required=True,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Absolute Path to the directory containing the python files"
                   " which generate the assembly tests. "
                   "Required Parameter")
@click.option('--gen_cvg',
              '-gc',
              is_flag=True,
              required=False,
              help='Set this flag to generate the Covergroups')
@click.option(
    '--gen_test_list',
    '-t',
    is_flag=True,
    required=False,
    help='Set this flag if a test-list.yaml is to be generated by utg. '
         'utg does not generate the test_list by default.')
@click.option('--linker_dir',
              '-ld',
              multiple=False,
              required=False,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Path to the working directory where generated files will be"
                   " stored.")
@click.option('--work_dir',
              '-wd',
              multiple=False,
              required=True,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Path to the working directory where generated files will be"
                   " stored.")
@click.option(
    '--modules',
    '-m',
    default='all',
    multiple=False,
    is_flag=False,
    help="Enter a list of modules as a string in a comma separated "
         "format.\n--module 'branch_predictor, decoder'\nHere "
         "decoder and branch_predictor are chosen\nIf all module "
         "are to be selected use keyword 'all'.\n Presently supported"
         "modules are: branch_predictor",
    type=str)
@click.option('--verbose',
              '-v',
              default='info', help='Set verbose level for debugging',
              type=click.Choice(['info', 'error', 'debug'],
                                case_sensitive=False))
@cli.command()
def generate(alias_file, dut_config, linker_dir, module_dir, gen_cvg,
             gen_test_list, work_dir, modules, verbose):
    """
    Generates tests, cover-groups for a list of modules corresponding to the DUT
    defined in dut_config inside the work_dir. Can also generate the test_list
    needed to execute them on RiverCore.\n
    Requires: -dc, --dut_config, -md, --module_dir; -wd, --work_dir\n
    Depends : (-gc, --gen_cvg -> -af, --alias_file)\n
    Optional: -gc, --gen_cvg; -t, --gen_test_list; -ld, --linker_dir;\n
              -m, --modules; -v, --verbose
    """

    logger.level(verbose)
    info(__version__)

    dut_dict = load_yaml(dut_config)
    generate_tests(work_dir=work_dir, linker_dir=linker_dir,
                   modules_dir=module_dir, modules=modules,
                   config_dict=dut_dict, test_list=gen_test_list,
                   verbose=verbose)
    if gen_cvg:
        if alias_file is not None:
            alias_dict = load_yaml(alias_file)
            generate_sv(work_dir=work_dir, config_dict=dut_dict,
                        modules_dir=module_dir, modules=modules,
                        alias_dict=alias_dict,
                        verbose=verbose)
        else:
            logger.error('Can not generate covergroups without alias_file.')
            exit('GEN_CVG WITHOUT ALIAS_FILE')


# -------------------------


@click.version_option(version=__version__)
@click.option('--module_dir',
              '-md',
              multiple=False,
              required=True,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Absolute Path to the directory containing the python files"
                   " which generate the assembly tests. "
                   "Required Parameter")
@cli.command()
def list_modules(module_dir):
    """
    Provides the list of modules supported from the module_dir\n
    Requires: -md, --module_dir
    """
    print(f'{list_of_modules(module_dir=module_dir)}')


# -------------------------


@click.option('--config_file',
              '-cf',
              multiple=False,
              required=False,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Provide a config.ini file's path. This runs utg based upon "
                   "the parameters stored in the file. If not specified "
                   "individual args/flags are to be passed through cli. In the"
                   "case of conflict between cli and config.ini values, config"
                   ".ini values will be chosen")
@cli.command()
def from_config(run_config):
    """
    This subcommand reads parameters from config.ini and runs utg based on the
    values.\n
    Optional: -cf, --config_file
    """

    config = ConfigParser()
    config.read(run_config)

    logger.level(config['utg']['verbose'])

    if config['utg']['clean']:
        logger.debug('Invoking clean_dirs')
        clean_dirs(work_dir=config['utg']['work_dir'],
                   modules_dir=config['utg']['module_dir'],
                   verbose=config['utg']['verbose'])
    if config['utg']['gen_test']:
        dut_dict = load_yaml(config['utg']['dut_config'])
        generate_tests(work_dir=config['utg']['work_dir'],
                       linker_dir=config['utg']['linker_dir'],
                       modules_dir=config['utg']['module_dir'],
                       modules=config['utg']['modules'],
                       config_dict=dut_dict,
                       test_list=config['utg']['gen_test_list'],
                       verbose=config['utg']['verbose'])
    if config['utg']['gen_cvg']:
        dut_dict = load_yaml(config['utg']['dut_config'])
        alias_dict = load_yaml(config['utg']['alias_file'])
        generate_sv(work_dir=config['utg']['work_dir'],
                    modules=config['utg']['modules'],
                    modules_dir=config['utg']['module_dir'],
                    config_dict=dut_dict,
                    alias_dict=alias_dict,
                    verbose=config['utg']['verbose'])
    if config['utg']['val_test']:
        dut_dict = load_yaml(config['utg']['dut_config'])
        validate_tests(modules=config['utg']['modules'],
                       work_dir=config['utg']['work_dir'],
                       config_dict=dut_dict,
                       modules_dir=config['utg']['module_dir'],
                       verbose=config['utg']['verbose'])

# -------------------------


@cli.command()
def setup():
    """
    Setups template files for config.ini, dut_config.yaml and aliasing.yaml\n
    """
    print(f'Files created')


# -------------------------

@click.version_option(version=__version__)
@click.option('--dut_config',
              '-dc',
              multiple=False,
              required=False,
              type=click.Path(resolve_path=True, readable=True),
              help="Path to the yaml file containing DUT configuration. "
                   "Needed to generate/validate tests")
@click.option('--module_dir',
              '-md',
              multiple=False,
              required=False,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Absolute Path to the directory containing the python files"
                   " which generate the assembly tests. "
                   "Required Parameter")
@click.option('--work_dir',
              '-wd',
              multiple=False,
              required=False,
              type=click.Path(exists=True, resolve_path=True, readable=True),
              help="Path to the working directory where generated files will be"
                   " stored.")
@click.option(
    '--modules',
    '-m',
    default='all',
    multiple=False,
    is_flag=False,
    help="Enter a list of modules as a string in a comma separated "
         "format.\n--module 'branch_predictor, decoder'\nHere "
         "decoder and branch_predictor are chosen\nIf all module "
         "are to be selected use keyword 'all'.\n Presently supported"
         "modules are: branch_predictor",
    type=str)
@click.option('--verbose',
              '-v',
              default='info',
              help='Set verbose level for debugging',
              type=click.Choice(['info', 'error', 'debug'],
                                case_sensitive=False))
@cli.command()
def validate(dut_config, module_dir, work_dir, modules, verbose):
    logger.level(verbose)
    info(__version__)
    dut_yaml = load_yaml(dut_config)
    validate_tests(modules=modules, work_dir=work_dir, config_dict=dut_yaml,
                   modules_dir=module_dir, verbose=verbose)
