# Copyright 2021 Tristan Keen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import find_packages, setup

with open("README.md") as f:
    readme = f.read()

with open("LICENSE") as f:
    license = f.read()

setup(
    name="heatmon",
    version="0.1.1",
    description="Heating statistics from OpenTRV",
    long_description=readme,
    author="Tristan Keen",
    author_email="tristan.keen@gmail.com",
    url="https://github.com/tyrken/heatmon",
    license=license,
    packages=find_packages(exclude=("tests", "docs", "misc")),
    entry_points="""
        [console_scripts]
        heatmon=heatmon.main:main
        set_trv_key=set_trv_key:main
    """,
)
