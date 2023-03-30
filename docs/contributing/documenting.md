# Documenting

This document outlines how to consistently document the modules, classes, and functions in pyggp. It mostly follows
the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).

## Modules

Modules should have a docstring at the top of the file, which should be a short description of the module. A license
boilerplate is *not* necessary.

```python
"""One line summary of the module, terminated by a period.

Optionally more detail description of the module, but only one-line summary is fine as well. Additionally, an Examples
section might be needed, but is not mandatory.

Examples:
    >>> import Foo
    >>> Foo.bar()
    'baz'

"""
```

Test modules are not required to have a docstring.

### Examples

- A module containing exceptions that all end with `TreeError`:

```python
"""Exceptions regarding Trees."""
```

- A module that contains multiple classes all concerned with handling a specific type of data:

```python
"""Classes for trees.

Provides classes for trees, including a base class for all trees, and a class for binary trees with optimizations
applied.

Examples:
    >>> import Tree
    >>> Tree.BinaryTree()
    <BinaryTree>
    >>> Tree.Tree()
    <Tree>

"""
```

- A module that contains a single class:

```python
"""Prime number sieve."""
```

- A module that contains functions:

```python
"""Functions for internationalization.

Mostly for internal use when logging messages.

"""
```

## Classes

Classes should have a docstring at the top of the class definition, which should be a short description of the class.
