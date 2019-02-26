# pw_unpack
Very simple Perfect World resource unpacker. Requires Python 3.

This supports the resource versions used in recent versions of Perfect World (tested on Mail.ru, PWI versions at 26.02.2019)
The main reason to create this was that existing tools online (sPCK and some weird GUI unpacker) do not support 64-bit archives -- and this tool does.

To unpack a file, just run, for example:
```
python unpack.py models.pkx
```

It will generate a directory called `models.files` with all the content inside.
NOTE that since this is written in Python it's quite slow compared to sPCK, especially with large data amounts.

However, it should be straightforward to rewrite it in C++ or update sPCK based on the changes (if anyone ever wants to do that)
