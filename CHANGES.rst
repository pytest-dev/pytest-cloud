Changelog
=========

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
