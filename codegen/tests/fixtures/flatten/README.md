# Flatten test fixtures

Two OpenAPI 3.1 specs exercise every structural path through `walk_any` where an
annotated object (`x-jsmn-type`) can be discovered. Combinational keywords
(`allOf`, `anyOf`, `oneOf`) are not covered yet.

## Specs

| File          | `$id`                     | Role                              |
| ------------- | ------------------------- | --------------------------------- |
| `spec_a.yaml` | `forge://test/main/v0`    | Entry points — walked by flatten  |
| `spec_b.yaml` | `forge://test/targets/v0` | `$ref` targets — in registry only |

## `walk_any` branches

| Branch | Trigger                            | Action                                          |
| ------ | ---------------------------------- | ------------------------------------------------ |
| **A**  | `type: object` + `x-jsmn-type` | Record struct, recurse into `properties`         |
| **B**  | `type: array`  + `x-jsmn-type` | Record CArray, recurse into `items`              |
| **B'** | `type: array`  (no annotation)     | Follow `items` (no decl emitted)                 |
| **C**  | `$ref`                             | Resolve via registry, recurse                    |
| **D**  | `type: string` + `x-jsmn-type`     | Record CArray (string typedef)                   |

## Test matrix

### Inline (spec_a only)

| Path    | Description                  | Entry schema      | Discovered names                                           |
| ------- | ---------------------------- | ----------------- | ---------------------------------------------------------- |
| A       | Top-level object             | `standalone`      | `standalone`                                               |
| A→A     | Nested inline property       | `parent`          | `parent`, `parent_child`                                   |
| A→B→A   | Inline array of objects      | `array_host`      | `array_host`, `array_item`                                 |
| A→B→A→A | Nested object in array items | `deep_array_host` | `deep_array_host`, `deep_array_entry`, `deep_array_detail` |

### Top-level arrays (spec_a only)

| Path  | Description                        | Entry schema    | Discovered names                |
| ----- | ---------------------------------- | --------------- | ------------------------------- |
| B→A   | Top-level array of inline objects  | `top_array`     | `top_array`, `top_array_item`   |
| B→C→A | Top-level array → $ref → object    | `top_arr_ref`   | `top_arr_ref`, `target_a`       |

### Top-level strings (spec_a only)

| Path | Description      | Entry schema | Discovered names |
| ---- | ---------------- | ------------ | ---------------- |
| D    | Top-level string | `top_string` | `top_string`     |

### Cross-spec $ref (spec_a → spec_b)

| Path      | Description                            | Entry schema     | Discovered names                               |
| --------- | -------------------------------------- | ---------------- | ---------------------------------------------- |
| A→C→A     | Property → $ref → object               | `ref_prop`       | `ref_prop`, `target_a`                         |
| A→C→A→A   | Property → $ref → object with child    | `ref_nested`     | `ref_nested`, `target_b`, `target_b_child`     |
| A→B→C→A   | Array items → $ref → object            | `arr_ref_items`  | `arr_ref_items`, `target_a`                    |
| A→C→B→A   | Property → $ref → array of objects     | `ref_to_array`   | `ref_to_array`, `target_c_item`                |
| A→B→C→A→A | Array items → $ref → object with child | `arr_ref_nested` | `arr_ref_nested`, `target_b`, `target_b_child` |
