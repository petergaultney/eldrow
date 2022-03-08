# eldrow

Run `env PYTHONSTARTUP=main.py ipython`

You now have various commands prefixed by `%`.

Most useful for helping solve That Which Must Not Be Named will be:

```
%scores
%guess
%options
%best_info
%best_options
```

If you want to play a random game, start with `%play`.

## TODO

1. ~~better input format~~
2. ~~improve scoring to maximze letter discovery when positions are known~~
3. ~~stricter/more correct matching when dealing with words with repeated characters~~
4. ~~Split code into at least 3 modules - the solver, the game module, and the IPython CLI.~~
5. Support non-ASCII wordlists - e.g. [Primel](https://converged.yt/primel/).
6. After first guess, attempt graph exploration of possibilities in order to result in fewest possible guesses.
