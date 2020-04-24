Changelog
=========

4.0.0
-----

- Add config option to select cipher for ssh connection (dasm)
- Fix deprecation warnings for pytest (dasm)
- Support pytest-xdist >= 1.26.0 (dasm)
- Support pytest >= 3.6.1 (dasm)
- Remove support for Python 3.0, 3.1, 3.2, 3.3 (consistent with pytest-xdist) (dasm)

3.0.1
-----

- support python 3.7 (bubenkoff)

3.0.0
-----

- support pytest-xdist >=1.22.1 (bubenkoff)

2.0.0
-----

- pytest fixed version number is removed from the requirements (olegpidsadnyi)
- removed pytest-cache dependency (olegpidsadnyi)

1.3.8
-----

- Add verbosity to rsync progress (bubenkoff)

1.3.4
-----

- Add develop eggs setting to install packages on remote side in development mode (bubenkoff)

1.2.16
------

- Correctly handle python path on remote side (bubenkoff)

1.2.12
------

- Add rsync progress to the output, change default bandwidth limit (bubenkoff)

1.2.11
------

- Fast native rsync instead of python based one (bubenkoff)

1.1.0
-----

- Avoid unnecessary multiple ssh connections to the same node (bubenkoff)

1.0.25
------

- Correct virtualenv execution (bubenkoff)

1.0.18
------

- Ensure plugin command line hook is executed first (bubenkoff)
- Correct free memory calculation (bubenkoff)

1.0.15
------

- Add pyc files cleanup (bubenkoff)

1.0.13
------

- Automatic discovery of the virtualenv (bubenkoff)
- Fixes to rsyncing (bubenkoff)
- Safer node id generation (bubenkoff)
- Guarantee uniqueness of provided nodes (bubenkoff)

1.0.10
------

- Delete orphan files when rsyncing (bubenkoff)


1.0.7
-----

- Add possibility to pass node list as space separated (bubenkoff)


1.0.6
-----

- Initial public release
