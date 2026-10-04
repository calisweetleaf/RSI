#ifndef RW_C_API_H
#define RW_C_API_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* All functions catch C++ exceptions. 0 is success; -1 is error.
 * rw_last_error is thread-local; copy it before making another API call.
 * Input buffers are copied. Output buffers belong to the caller.
 */
typedef struct rw_system rw_system;
rw_system *rw_create(void);
void rw_destroy(rw_system *system);
const char *rw_last_error(void);
int rw_load(rw_system *system, const char *path);
int rw_save(const rw_system *system, const char *path);
int rw_set_codebook(rw_system *system, const float *values, size_t rows, size_t cols);
int rw_add_weight_file(rw_system *system, const char *key, const char *path);
int rw_remove_weight(rw_system *system, const char *key);
int rw_weight_dimension(const rw_system *system, const char *key, size_t *dimension);
int rw_evaluate(rw_system *system, const char *key, uint32_t depth, double time,
                int python_semantics, float *output, size_t output_count);
int rw_mutate(rw_system *system, const char *key, uint32_t mutation_type, double strength,
              uint32_t seed);
#ifdef __cplusplus
}
#endif
#endif
