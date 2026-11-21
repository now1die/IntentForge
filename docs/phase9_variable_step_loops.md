# Variable-step loops

A step expression may depend on integer parameters or previously evaluated
invariant locals. The model refuses writes to the induction variable in the
loop body and excludes the mutable carriers from bound and step terms.

On each supplied input, the normalized guard determines the direction and
whether the body runs. When it runs, the step must make progress in that
direction with a magnitude from 1 through 64. Each summarized progression has
at most 64 points. It checks the last latch and all modeled scalar arithmetic
against int32 limits. Zero-iteration inputs skip the latch. Unknown direction
or progress on an entered loop causes abstention.

These checks describe the supplied inputs. The summary does not prove
termination over a larger declared domain.
