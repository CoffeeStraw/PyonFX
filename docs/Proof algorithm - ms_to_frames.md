# ms_to_frames
To convert an frame to an ms, here is the formula: $$ms = frame * {1 \over fps} * 1000$$
But depending on what the user want, he may need to floor the result or round it (see docs of timestamps.py for more information)
Important to note, $frame \in \mathbb{N}$. This means we need to take the **integer** between the 2 bounds of the inequations that are detailed below.

## Explanation for rounding method

Important to note, here the rounding method round up, so, if it encounter $round(x.5)$, it will become $x + 1$

From the previous equation, we can deduce this:
$$ms - 0.5 \le frame * {1 \over fps} * 1000 < ms + 0.5$$

And from the previous inequation, we can isolate $frame$ like this:
$$(ms - 0.5) * fps * {1 \over 1000} \le frame < (ms + 0.5) * fps * {1 \over 1000}$$

Algorithm:
```py
# We use the upper bound
upper_bound = (ms + 0.5) * fps * 1/1000
# Then, we trunc the result
trunc_frame = int(upper_bound)

# If the upper_bound equals to the trunc_frame, this means that we don't respect the inequation because it is "greater than", not "greater than or equals".
# So if it happens, this means we need to return the previous frame
if upper_bound == trunc_frame:
    return trunc_frame - 1
else:
    return trunc_frame
```


## Explanation for floor method

From the previous equation, we can deduce this:
$$ms \le frame * {1 \over fps} * 1000 < ms + 1$$

And from the previous inequation, we can isolate $frame$ like this:
$$ms * fps * {1 \over 1000} \le frame < (ms + 1) * fps * {1 \over 1000}$$

Algorithm:
```py
# We use the upper bound
upper_bound = (ms + 1) * fps * 1/1000
# Then, we trunc the result
trunc_frame = int(upper_bound)

# If the upper_bound equals to the trunc_frame, this means that we don't respect the inequation because it is "greater than", not "greater than or equals".
# So if it happens, this means we need to return the previous frame
if upper_bound == trunc_frame:
    return trunc_frame - 1
else:
    return trunc_frame
```
