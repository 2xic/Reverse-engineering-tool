


#define VALUE_INT 0 
#define VALUE_VECTOR 1
#define VALUE_VECTOR_INT 2
#define VALUE_MEMORY 3

#define VECTOR_SIZE 12


struct vector_stucture_pointer {
	int max_capacity;
	char *keyword;
	int size;
	int type;
	int malloc_keyword;
	void **items;
};

struct vector_stucture_pointer *init_vector_pointer(void *keyword);
void *vector_add_pointer(struct vector_stucture_pointer *vector, void*item);
void *vector_get_pointer(struct vector_stucture_pointer *vector, int index);
void free_vector_pointer(struct vector_stucture_pointer *vector);