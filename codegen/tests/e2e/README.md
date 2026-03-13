# e2e tests

## Build and run

```sh
cmake -B ./build -S ./e2e
cmake --build ./build
ctest --test-dir ./build
```
