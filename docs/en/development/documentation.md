# Documentation

The documentation is generated using `mkdocs` utility which can generate documentation from
different sources. All content should be written using markdown syntax.

All the documentation will reside in the `docs/en/` folder and is currently only in
english available.

## Writing

Reviewing the documentation locally can be done by using the following command, which
makes it available via [http://127.0.0.1:8000/](http://127.0.0.1:8000/):


```
mkdocs serve
```

## Publishing

To publish committed documentation in the documentation folder, run the following
command:


```
mkdocs gh-deploy
git push origin gh-pages
```

This will automatically start the publishing process and make the documentation avilable
in a few seconds at [https://framarama.github.io/](https://framarama.github.io/).

