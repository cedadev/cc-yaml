import importlib
import yaml

from compliance_checker.base import BaseCheck


class YamlParser(object):
    """
    Class to hold methods relating to generating a checker class from a YAML
    config file
    """

    @classmethod
    def get_checker_class(cls, config):
        """
        Parse the given YAML file and return a checker class

        :param config: Config dictionary or filename of YAML file to parse
                       config from
        :return:       A class that can be used as a check suite with
                       compliance-checker
        """
        # Treat config as a filename if it is a string
        if isinstance(config, str):
            with open(config) as f:
                config = yaml.load(f)

            if not isinstance(config, dict):
                raise TypeError("Could not parse dictionary from YAML file")

        cls.validate_config(config)

        # Build the attributes and methods for the generated class
        class_properties = {}

        supported_ds_sets = []

        for check_info in config["checks"]:
            method_name = "check_{}".format(check_info["check_id"])

            # Instantiate a check object using the params from the config
            parts = check_info["check_name"].split(".")
            module = importlib.import_module(".".join(parts[:-1]))
            check_cls = getattr(module, parts[-1])

            # Validate parameters
            params = {}
            params.update(check_cls.defaults)
            params.update(check_info["parameters"])
            if hasattr(check_cls, "required_parameters"):
                try:
                    for key, expected_type in check_cls.required_parameters.items():
                        cls.validate_field(key, expected_type, params, True)
                except (ValueError, TypeError) as ex:
                    msg = "Invalid parameters in YAML file: {}".format(ex)
                    raise ex.__class__(msg)

            level_str = check_info.get("check_level", None)
            check_instance = check_cls(params, level=level_str)

            # Create function that will become method of the new class. Specify
            # check_instance as a default argument so that it is evaluated when
            # function is defined - otherwise the function stores a reference
            # to check_instance which changes as the for loop progresses, so
            # only the last check is run
            def inner(self, ds, c=check_instance):
                return c.do_check(ds)

            inner.__name__ = str(method_name)
            class_properties[method_name] = inner
            supported_ds_sets.append(set(check_cls.supported_ds))

        # Supported dataset types will be those that are supported by ALL checks
        class_properties["supported_ds"] = list(set.intersection(*supported_ds_sets))

        return type(config["suite_name"], (BaseCheck,), class_properties)

    @classmethod
    def validate_config(cls, config):
        """
        Validate a config dict to check it has all the information required to
        generate a checker class

        :param config: The dictionary parsed from YAML file to check
        :raises ValueError: if any required values are missing or invalid
        :raises TypeError:  if any values are an incorrect type
        """
        required_global = {"checks": list, "suite_name": str}
        required_percheck = {"check_id": str, "parameters": dict, "check_name": str}
        optional_percheck = {"check_level": str}

        for f_name, f_type in required_global.items():
            cls.validate_field(f_name, f_type, config, True)

        for check_info in config["checks"]:
            for f_name, f_type in required_percheck.items():
                cls.validate_field(f_name, f_type, check_info, True)

            for f_name, f_type in optional_percheck.items():
                cls.validate_field(f_name, f_type, check_info, False)

            allowed_levels = ("HIGH", "MEDIUM", "LOW")
            if "check_level" in check_info and check_info["check_level"] not in allowed_levels:
                raise ValueError("Check level must be one of {}".format(", ".join(allowed_levels)))

        if len(config["checks"]) == 0:
            raise ValueError("List of checks cannot be empty")

    @classmethod
    def validate_field(cls, key, val_type, d, required):
        """
        Helper method to check a dictionary contains a given key and that the
        value is the correct type
        """
        if required and key not in d:
            raise ValueError("Required key '{}' not present".format(key))

        if key in d and not isinstance(d[key], val_type):
            err_msg = "Value for field '{}' is not of type '{}'"
            raise TypeError(err_msg.format(key, val_type.__name__))
