from cc_yaml.yaml_parser import YamlParser


class SuiteGenerator(object):
    """
    Interface between compliance-checker plugin system and YAML loading.
    Provides methods to get checker classes based on command-line arguments.
    """

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("-y", "--yaml", action="append", dest="yaml_files",
                            default=[], help="Specify YAMl files to generate "
                                             "check suites from")

    @classmethod
    def get_suites(cls, args):
        """
        :param args: argparse arguments object
        :return:     dictionary mapping check name to checker class
        """
        suites = {}
        for filename in args.yaml_files:
            suite = YamlParser.get_checker_class(filename)
            suites[suite.__name__] = suite
        return suites
