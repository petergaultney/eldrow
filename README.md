# eldrow

Run `env PYTHONSTARTUP=eldrow.py ipython`

Then, run `%load_ext eldrow`

You now have various commands prefixed by `%`.

Most useful will be:

```
%scores
%g
%options
%best_info
%best_options
```

## TODO

1. ~~better input format~~
2. ~~improve scoring to maximze letter discovery when positions are known~~
3. stricter/more correct matching when dealing with words with repeated characters
4. After first guess, attempt graph exploration of possibilities in order to result in fewest possible guesses.
