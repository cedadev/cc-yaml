"""
Test the generation of a checker class from a YAML file
"""
import pytest
import inspect
from copy import deepcopy

from cc_yaml.yaml_parser import YamlParser
from checklib.register import ParameterisableCheckBase
from compliance_checker.base import BaseCheck


# Create test checks for checking the supported_ds property in the generated
# check class. For simplicity here dataset types are ints
class SupportDsTestCheckClass1(ParameterisableCheckBase):
    supported_ds = [1, 2, 3]


class SupportDsTestCheckClass2(ParameterisableCheckBase):
    supported_ds = [2, 3, 4]


# Create base check used to test that the parameters in the config are
# validated against required_parameters property in the base check
class RequiredParamsTestCheckClass(ParameterisableCheckBase):
    required_parameters = {
        "one": str, "two": list, "three": dict, "four": int
    }


# Base check to test default parameters
class DefaultParamsTestCheckClass(ParameterisableCheckBase):
    defaults = {"one": "hello"}
    required_parameters = {"one": str}

    def do_check(self, ds):
        """Return parameter here so we can check it is present in the test"""
        return self.kwargs["one"]


class TestYamlParsing(object):

    def get_import_string(self, cls):
        """
        Return a string to use as 'check_name' in YAML configs in tests to
        import a class from this file
        """
        return "{}.{}".format("cc_yaml.tests", cls)

    def test_missing_keys(self):
        """
        Check that a config with missing required fields is marked as invalid
        """
        invalid_configs = [
            {},
            {"suite_name": "hello"},  # Missing checks
            {"checks": []},           # Missing suite name
            # Missing parameters
            {"suite_name": "hello", "checks": [{"check_id": "one"}]}
        ]
        valid_config = {"suite_name": "hello",
                        "checks": [{"check_id": "one", "parameters": {},
                                    "check_name": "blah"}]}

        for c in invalid_configs:
            with pytest.raises(ValueError):
                YamlParser.validate_config(c)
        try:
            YamlParser.validate_config(valid_config)
        except ValueError:
            assert False, "Valid config was incorrectly marked as invalid"

    def test_invalid_types(self):
        """
        Check that configs are marked as invalid if elements in it are of the
        wrong type
        """
        # Start with a valid config
        valid_config = {"suite_name": "hello",
                        "checks": [{
                            "check_id": "one", "parameters": {},
                            "check_name": "checklib.register.FileSizeCheck"
                        }]}

        c1 = deepcopy(valid_config)
        c1["suite_name"] = ("this", "is", "not", "a", "string")

        c2 = deepcopy(valid_config)
        c2["checks"] = "oops"

        c3 = deepcopy(valid_config)
        c3["checks"][0]["check_id"] = {}

        c4 = deepcopy(valid_config)
        c4["checks"][0]["parameters"] = 0

        for c in (c1, c2, c3, c4):
            with pytest.raises(TypeError):
                YamlParser.validate_config(c)

    def test_no_checks(self):
        """
        Check that a config with no checks is invalid
        """
        with pytest.raises(ValueError):
            YamlParser.validate_config({"suite_name": "test", "checks": []})

    def test_class_gen(self):
        """
        Check that a checker class is generated correctly
        """
        # TODO: Confirm that the base check actually runs
        check_cls = "checklib.register.FileSizeCheck"
        config = {
            "suite_name": "test_suite",
            "checks": [
                {"check_id": "one", "parameters": {}, "check_name": check_cls},
                {"check_id": "two", "parameters": {}, "check_name": check_cls}
            ]
        }
        new_class = YamlParser.get_checker_class(config)
        # Check class inherits from BaseCheck
        assert BaseCheck in new_class.__bases__

        # Check the expected methods are present
        method_names = [x[0] for x in inspect.getmembers(new_class, inspect.ismethod)]
        assert "check_one" in method_names
        assert "check_two" in method_names

        # Check name is correct
        assert new_class.__name__ == "test_suite"

    def test_supported_ds(self):
        valid_config = {
            "suite_name": "test_suite",
            "checks": [
                {"check_id": "one", "parameters": {},
                 "check_name": self.get_import_string("SupportDsTestCheckClass1")},

                {"check_id": "one", "parameters": {},
                 "check_name": self.get_import_string("SupportDsTestCheckClass2")}
            ]
        }
        check_cls = YamlParser.get_checker_class(valid_config)
        # Supported datasets for generated class should be types common to both
        # checks
        assert check_cls.supported_ds == [2, 3]

    def test_parameter_validation(self):
        """
        Check that the parameters section of the config is validated against
        the required parameters for the base check
        """
        invalid_params = [
            # "three" missing
            ({"one": "string here", "two": ["list", "of", "things"],
              "four": 14}, ValueError),

            # "one" wrong type
            ({"one": ["not", "a", "string"], "two": [1, 2], "three": {1: 2},
              "four": 14}, TypeError)
        ]

        check_name = self.get_import_string("RequiredParamsTestCheckClass")
        config = {
            "suite_name": "test_suite",
            "checks": [{"check_id": "one", "parameters": {},
                        "check_name": check_name}]
        }

        for params, ex in invalid_params:
            config["checks"][0]["parameters"] = params

            with pytest.raises(ex):
                checker_cls = YamlParser.get_checker_class(config)

        # Try one with valid params and check no exceptions raised
        config["checks"][0]["parameters"] = {
            "one": "string here",
            "two": ["list", "of", "things"],
            "three": {1: 2},
            "four": 14
        }
        try:
            checker_cls = YamlParser.get_checker_class(config)
        except (ValueError, TypeError) as ex:
            assert False, "Valid config was incorrectly marked as invalid: {}".format(ex)

    def test_default_parameters(self):
        """
        Check that missing parameters are copied over from the 'defaults'
        property when generating a check class
        """
        config = {
            "suite_name": "test_suite",
            "checks": [{"check_id": "one", "parameters": {},
                        "check_name": self.get_import_string("DefaultParamsTestCheckClass")}]
        }
        try:
            checker_cls = YamlParser.get_checker_class(config)
        except ValueError:
            assert False, ("Config marked as invalid due to missing field - "
                           "defaults probably not copied over")
        checker = checker_cls()
        try:
            val = checker.check_one("dataset")
        except KeyError:
            assert False, "Default parameter not copied"

        assert val == "hello"
