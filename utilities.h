#ifndef UTILITIES_H
#define UTILITIES_H

void nrerror(char error_text[]);
void free_ivector(int *v, long nl, long nh);
void free_vector(float *v, long nl, long nh);
void free_matrix(float **m, long nrl,long nrh,long ncl,long nch);
float *vector(long nl, long nh);
int *ivector(long nl, long nh);
float **matrix(long nrl, long nrh, long ncl, long nch);
void indexx(int n, float arr[], int indx[]);
void fileerrorcheck(FILE *fp);

#endif /* UTILITIES_H*/