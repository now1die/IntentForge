# Coordinate contracts

The supported layout is a literal-size local array with a return address of the form `row * width + column`. Independent entry parameter bindings identify the axes. The physical extent must divide evenly by the positive literal width. The inferred signed ranges are `0 <= row < height` and `0 <= column < width`, with separate static and sampled evidence. One valid axis can coexist with an invalid or unknown other axis.

A candidate extends an existing complete signed one-axis rejection guard with the second axis. Discovery must include invalid inputs below and above the second axis and an in-bounds input. A rectangular authored control verifies that the width and height are distinct. Dynamic logical dimensions including zero-size grids, arbitrary strides, nested arrays and the full upstream Saddleback algorithm are outside this repair grammar.
