# cc-yaml

This repo holds a [compliance-checker](https://github.com/ioos/compliance-checker)
plugin that generates check suites from YAML descriptions.

It is to be used with the [generator-plugins branch](https://github.com/joesingo/compliance-checker/tree/generator-plugins)
of my fork of `compliance-checker` which is still a work in progress.

## Installation

To set up you must install `compliance-checker` itself, this plugin (`cc-yaml`)
and `compliance-check-lib`.

```
pip install -e git+https://github.com/joesingo/compliance-checker@generator-plugins
pip install -e git+https://github.com/joesingo/cc-yaml
pip install -e git+https://github.com/joesingo/compliance-check-lib

compliance-checker --yaml <path-to-YAML-file> --test <test name> <dataset>
```

## Creating check suites from YAML descriptions

This plugin allows check suites to be generated from *base checks* using YAML
files containing parameters to call these base checks with.

Currently all available *base checks* are in the [compliance-check-lib](https://github.com/joesingo/compliance-check-lib)
repo (along with the base class required to create your own checks).

### Example

An example YAML file is shown below.

```yaml
suite_name: "custom-check-suite"

checks:
  - check_id: "filesize_check"
    parameters: {"threshold": 1}
    check_name: "checklib.register.FileSizeCheck"

  - check_id: "filename_check"
    parameters: {"delimiter": "_", "extension": ".nc"}
    check_name: "checklib.register.FileNameStructureCheck"

  - check_id: "attribute_check"
    parameters: {"regex": "\\d+", "attribute": "author"}
    check_name: "checklib.register.GlobalAttrRegexCheck"
    check_level: "LOW"
```

Explanation:

* `suite_name` (in this example 'custom-check-suite') is the name of the generated suite (i.e. the
  name to use after `--test` when running Compliance Checker from the command line)
* Each item in the list `checks` defines a single check method:
  * `check_id` is an identifier for the check (the identifier used is somewhat arbitrary, and is
    only used for the name of the check method in the generated class)
  * `check_name` is the *base check* where the actual code to perform the check is defined. It
    should be of the form `<module>.class`. This module needs to be importable from the environment
    in which Compliance Checker is run. Details on what this class should look like are given below.
  * `parameters` is a dictionary that is passed to `__init__` when instantiating the class
    specified in `check_name`.
  * `check_level` is one of `HIGH`, `MEDIUM`, `LOW` and determines the priority level of the check.

This check suite can be run from the command line by using the `--yaml` option:
```
compliance-checker --yaml <path-to-YAML-file> --test custom-check-suite <dataset>
```

### Base Checks

Each base check is represented as a sub-class of the `ParameterisableCheckBase` class in
`compliance-check-lib`. A simple example showing all the available functionality is shown
below. The actual check performed tests if the filename of a dataset contains a given
substring.

```python
from compliance_checker.base import Result, Dataset, GenericFile

from checklib.register import ParameterisableCheckBase


class SubstringCheck(ParameterisableCheckBase):

    supported_ds = [Dataset, GenericFile]
    short_name = "Substring check: '{string}'"
    message_templates = ["Filename does not contain '{string}' as a substring"]
    level = "MEDIUM"
    defaults = {"string": "default-substring"}
    required_parameters = {"string": str, "some_other_param": dict}

    def _setup(self):
        # Override this method to perform validation or modification of arguments
        pass

    def _check_primary_arg(self, ds):
        # Override this method to perform any checks on the dataset before
        # running the check
        pass

    def _get_result(self, ds):
        messages = []
        if self.kwargs["string"] in ds.filepath():
            score = self.out_of
        else:
            score = 0
            messages.append(self.get_messages()[0])

        return Result(self.level, (score, self.out_of), self.get_short_name(),
                      messages)
```

Properties:

* `supported_ds` should be a list of dataset types acceptable to run this check
  on, as with the `supported_ds` property in usual check suite classes. If not
  given it default to `Dataset` only.
* `short_name` is a template string for the name of the check that can be shown
  in the output. It is constructed by calling `self.get_short_name()`, which uses
  standard python string formatting by passing the parameters given in the YAML
  config as keyword arguments to the `format` method.
* `message_templates` is a list of strings to be used as error messages if parts
  of the check fail. They can be retrieved with `self.get_messages()` and are
  formatted in the same way as `short_name`. The length of this list determines
  `self.out_of`, which is the number of points available for the check.
* `level` is one of HIGH, MEDIUM or LOW and can be used when returning the
  `Result` object for the check (the value specified here is the default - it
  can be overridden in the YAML config).
* `defaults` is a dictionary containing the default parameters to use for the
  check for any parameters not specified in the YAML config.
* `required_parameters` is a dictionary listing all parameters that *must* be
  present in the YAML config, and the types they should be (e.g. `str`, `list`,
  `int`, `float`, `dict` etc...). An error is thrown when parsing the YAML
  config if any parameters are missing or of an incorrect type.

Methods:

* `_setup` is called after the class is initialised and before the check is run.
* `_check_primary_arg` is called when the check is run, and if passed the dataset as an argument.
  Raise a `FileError` from here (from `checklib.code.errors`) to cancel the check and return a
  score of 0.
* `_get_result` is called after `_check_primary_arg` and is where the actual checking happens.
  Parameters from the YAML config are stored as a dictionary in `self.kwargs`.
  This method should return a `Result` object in the same way an ordinary check method would.
