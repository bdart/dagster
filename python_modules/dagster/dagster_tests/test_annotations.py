import sys
from abc import abstractmethod
from typing import NamedTuple, get_type_hints

import pytest
from dagster import resource
from dagster._annotations import (
    PUBLIC,
    PublicAttr,
    deprecated,
    experimental,
    get_deprecated_info,
    get_experimental_info,
    is_deprecated,
    is_experimental,
    is_public,
    public,
)
from dagster._utils.backcompat import ExperimentalWarning
from typing_extensions import Annotated

from dagster_tests.general_tests.utils_tests.utils import assert_no_warnings


def compose_decorators(*decorators):
    def _decorator(fn):
        for decorator in reversed(decorators):
            fn = decorator(fn)
        return fn

    return _decorator


# ########################
# ##### PUBLIC
# ########################


def test_public_method():
    class Foo:
        @public
        def bar(self):
            pass

    assert is_public(Foo.bar)


@pytest.mark.parametrize(
    "decorators",
    [
        (public, property),
        (property, public),
        (public, staticmethod),
        (staticmethod, public),
        (public, classmethod),
        (classmethod, public),
        (public, abstractmethod),
        (abstractmethod, public),
    ],
    ids=[
        "public-property",
        "property-public",
        "public-staticmethod",
        "staticmethod-public",
        "public-classmethod",
        "classmethod-public",
        "public-abstractmethod",
        "abstractmethod-public",
    ],
)
def test_public_multi_decorator(decorators):
    class Foo:
        @compose_decorators(*decorators)
        def bar(self):
            pass

    assert is_public(Foo.__dict__["bar"])  # __dict__ for descriptor access


def test_public_attribute():
    class Foo(NamedTuple("_Foo", [("bar", PublicAttr[int])])):
        pass

    hints = (
        get_type_hints(Foo, include_extras=True)
        if sys.version_info >= (3, 9)
        else get_type_hints(Foo)
    )
    assert hints["bar"] == Annotated[int, PUBLIC]


# ########################
# ##### DEPRECATED
# ########################

# In the below tests, we don't check the category at the start of the error message ("Function",
# "Class method", "Property", etc) because this unfortunately depends on the ordering of the
# decorators:
#
# @deprecated
# @property
# def foo(self):  # "Property `foo` is deprecated..."

# @deprecated
# @property
# def foo(self):  # "Function `foo` is deprecated..."

deprecated_bound = deprecated(breaking_version="2.0", additional_warn_text="foo")


def test_deprecated_method():
    class Foo:
        @deprecated_bound
        def bar(self):
            pass

    assert is_deprecated(Foo.bar)
    assert get_deprecated_info(Foo.bar).breaking_version == "2.0"

    with pytest.warns(
        DeprecationWarning,
        match=r"Function `[^`]+Foo.bar` is deprecated and will be removed in 2.0",
    ):
        Foo().bar()


@pytest.mark.parametrize(
    "decorators",
    [
        (deprecated_bound, property),
        (property, deprecated_bound),
    ],
    ids=[
        "deprecated-property",
        "property-deprecated",
    ],
)
def test_deprecated_property(decorators):
    class Foo:
        @compose_decorators(*decorators)
        def bar(self):
            return 1

    assert is_deprecated(Foo.__dict__["bar"])  # __dict__ access to get property

    with pytest.warns(
        DeprecationWarning, match=r"`[^`]+Foo.bar` is deprecated and will be removed in 2.0"
    ) as warning:
        assert Foo().bar
    assert warning[0].filename.endswith("test_annotations.py")


@pytest.mark.parametrize(
    "decorators",
    [
        (deprecated_bound, staticmethod),
        (staticmethod, deprecated_bound),
    ],
    ids=[
        "deprecated-staticmethod",
        "staticmethod-deprecated",
    ],
)
def test_deprecated_staticmethod(decorators):
    class Foo:
        @compose_decorators(*decorators)
        def bar():
            pass

    assert is_deprecated(Foo.__dict__["bar"])  # __dict__ access to get descriptor

    with pytest.warns(
        DeprecationWarning, match=r"`[^`]+Foo.bar` is deprecated and will be removed in 2.0"
    ) as warning:
        Foo.bar()
    assert warning[0].filename.endswith("test_annotations.py")


@pytest.mark.parametrize(
    "decorators",
    [
        (deprecated_bound, classmethod),
        (classmethod, deprecated_bound),
    ],
    ids=[
        "deprecated-classmethod",
        "classmethod-deprecated",
    ],
)
def test_deprecated_classmethod(decorators):
    class Foo:
        @compose_decorators(*decorators)
        def bar(self):
            pass

    assert is_deprecated(Foo.__dict__["bar"])  # __dict__ access to get descriptor

    with pytest.warns(
        DeprecationWarning, match=r"`[^`]+Foo.bar` is deprecated and will be removed in 2.0"
    ) as warning:
        Foo.bar()
    assert warning[0].filename.endswith("test_annotations.py")


@pytest.mark.parametrize(
    "decorators",
    [
        (deprecated_bound, abstractmethod),
        (abstractmethod, deprecated_bound),
    ],
    ids=[
        "deprecated-abstractmethod",
        "abstractmethod-deprecated",
    ],
)
def test_deprecated_abstractmethod(decorators):
    class Foo:
        @compose_decorators(*decorators)
        def bar(self):
            ...

    assert is_deprecated(Foo.bar)  # __dict__ access to get descriptor


def test_deprecated_class():
    @deprecated_bound
    class Foo:
        def bar(self):
            ...

    assert is_deprecated(Foo)

    with pytest.warns(
        DeprecationWarning, match=r"Class `[^`]+Foo` is deprecated and will be removed in 2.0"
    ) as warning:
        Foo()
    assert warning[0].filename.endswith("test_annotations.py")


def test_deprecated_namedtuple_class():
    @deprecated_bound
    class Foo(NamedTuple("_", [("bar", str)])):
        pass

    with pytest.warns(
        DeprecationWarning, match=r"Class `[^`]+Foo` is deprecated and will be removed in 2.0"
    ) as warning:
        Foo(bar="ok")
    assert warning[0].filename.endswith("test_annotations.py")


def test_deprecated_resource():
    @deprecated_bound
    @resource
    def foo():
        ...

    assert is_deprecated(foo)

    with pytest.warns(
        DeprecationWarning,
        match=r"Dagster resource `[^`]+foo` is deprecated and will be removed in 2.0",
    ) as warning:
        foo()
        assert warning[0].filename.endswith("test_annotations.py")


########################
##### EXPERIMENTAL
########################


def test_experimental_method():
    class Foo:
        @experimental(additional_warn_text="baz")
        def bar(self):
            pass

    assert is_experimental(Foo.bar)
    assert get_experimental_info(Foo.bar).additional_warn_text == "baz"

    with pytest.warns(ExperimentalWarning, match=r"`[^`]+Foo.bar` is experimental") as warning:
        Foo().bar()
    assert warning[0].filename.endswith("test_annotations.py")


@pytest.mark.parametrize(
    "decorators",
    [
        (experimental, property),
        (property, experimental),
    ],
    ids=[
        "experimental-property",
        "property-experimental",
    ],
)
def test_experimental_property(decorators):
    class Foo:
        @compose_decorators(*decorators)
        def bar(self):
            return 1

    assert is_experimental(Foo.__dict__["bar"])  # __dict__ access to get descriptor

    with pytest.warns(ExperimentalWarning, match=r"`[^`]+Foo.bar` is experimental") as warning:
        assert Foo().bar
    assert warning[0].filename.endswith("test_annotations.py")


@pytest.mark.parametrize(
    "decorators",
    [
        (experimental, staticmethod),
        (staticmethod, experimental),
    ],
    ids=[
        "experimental-staticmethod",
        "staticmethod-experimental",
    ],
)
def test_experimental_staticmethod(decorators):
    class Foo:
        @compose_decorators(*decorators)
        def bar():
            pass

    assert is_experimental(Foo.__dict__["bar"])  # __dict__ access to get descriptor

    with pytest.warns(ExperimentalWarning, match=r"`[^`]+Foo.bar` is experimental") as warning:
        Foo.bar()
    assert warning[0].filename.endswith("test_annotations.py")


@pytest.mark.parametrize(
    "decorators",
    [
        (experimental, classmethod),
        (classmethod, experimental),
    ],
    ids=[
        "experimental-classmethod",
        "classmethod-experimental",
    ],
)
def test_experimental_classmethod(decorators):
    class Foo:
        @compose_decorators(*decorators)
        def bar(self):
            pass

    assert is_experimental(Foo.__dict__["bar"])  # __dict__ access to get descriptor

    with pytest.warns(ExperimentalWarning, match=r"`[^`]+Foo.bar` is experimental") as warning:
        Foo.bar()
    assert warning[0].filename.endswith("test_annotations.py")


@pytest.mark.parametrize(
    "decorators",
    [
        (experimental, abstractmethod),
        (abstractmethod, experimental),
    ],
    ids=[
        "experimental-abstractmethod",
        "abstractmethod-experimental",
    ],
)
def test_experimental_abstractmethod(decorators):
    class Foo:
        @compose_decorators(*decorators)
        def bar(self):
            ...

    assert is_experimental(Foo.bar)


def test_experimental_class():
    @experimental
    class Foo:
        def bar(self):
            ...

    assert is_experimental(Foo)

    with pytest.warns(ExperimentalWarning, match=r"`[^`]+Foo` is experimental") as warning:
        Foo()
    assert warning[0].filename.endswith("test_annotations.py")


def test_experimental_class_with_methods():
    @experimental
    class ExperimentalClass:
        def __init__(self, salutation="hello"):
            self.salutation = salutation

        def hello(self, name):
            return f"{self.salutation} {name}"

    @experimental
    class ExperimentalClassWithExperimentalFunction(ExperimentalClass):
        def __init__(self, sendoff="goodbye", **kwargs):
            self.sendoff = sendoff
            super().__init__(**kwargs)

        @experimental
        def goodbye(self, name):
            return f"{self.sendoff} {name}"

    with pytest.warns(
        ExperimentalWarning,
        match=r"`[^`]+ExperimentalClass` is experimental",
    ):
        experimental_class = ExperimentalClass(salutation="howdy")

    with assert_no_warnings():
        assert experimental_class.hello("dagster") == "howdy dagster"

    with pytest.warns(
        ExperimentalWarning,
        match=r"Class `[^`]+ExperimentalClassWithExperimentalFunction` is experimental",
    ):
        experimental_class_with_experimental_function = ExperimentalClassWithExperimentalFunction()

    with assert_no_warnings():
        assert experimental_class_with_experimental_function.hello("dagster") == "hello dagster"

    with pytest.warns(
        ExperimentalWarning,
        match=r"Function `[^`]+goodbye` is experimental",
    ):
        assert experimental_class_with_experimental_function.goodbye("dagster") == "goodbye dagster"

    @experimental
    class ExperimentalNamedTupleClass(NamedTuple("_", [("salutation", str)])):
        pass

    with pytest.warns(
        ExperimentalWarning,
        match=r"`[^`]+ExperimentalNamedTupleClass` is experimental",
    ):
        assert ExperimentalNamedTupleClass(salutation="howdy").salutation == "howdy"


def test_experimental_namedtuple_class():
    @experimental
    class Foo(NamedTuple("_", [("bar", str)])):
        pass

    with pytest.warns(ExperimentalWarning, match=r"Class `[^`]+Foo` is experimental") as warning:
        Foo(bar="ok")
    assert warning[0].filename.endswith("test_annotations.py")


def test_experimental_resource():
    @experimental
    @resource
    def foo():
        ...

    assert is_experimental(foo)

    with pytest.warns(
        ExperimentalWarning,
        match=r"Dagster resource `[^`]+foo` is experimental",
    ) as warning:
        foo()
        assert warning[0].filename.endswith("test_annotations.py")


# ########################
# ##### OTHER
# ########################


def test_all_annotations():
    @public
    @deprecated(breaking_version="2.0", additional_warn_text="foo")
    @experimental
    def foo():
        pass

    assert is_public(foo)
    assert is_deprecated(foo)
    assert is_experimental(foo)

    with pytest.warns(ExperimentalWarning, match=r"`[^`]+foo` is experimental") as warning:
        foo()
    assert warning[0].filename.endswith("test_annotations.py")

    with pytest.warns(DeprecationWarning, match=r"`[^`]+foo` is deprecated") as warning:
        foo()
    assert warning[0].filename.endswith("test_annotations.py")
