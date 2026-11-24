---
id: a-virtualenv-on-path-shadows-system-python
title: A virtualenv on PATH shadows the system Python for every later step
repos: [all]
domains: [ci]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

The superbuild job put vcstool's virtualenv on `PATH`. CMake then found the virtualenv's python, which had none of
the system modules (python-dbus), and a tray test failed with "No module named 'dbus'". Call a tool in a virtualenv
by its full path, and keep the virtualenv off `PATH`.
