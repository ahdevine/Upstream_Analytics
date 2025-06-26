/*
 computes upstream average of input array, normalized by drainage area

 expects input DEM at ./data/input/DEM.flt
 expects input contributing area raster at ./data/input/contribarea.flt

 two command-line arguments:
    first is the path to the input raster to be averaged
    second is the path to write the output averaged raster

 compile with:
    gcc -o upstreamavg.exe upstreamavg.c utilities.c -lm
 run with, e.g.:
    ./upstreamavg.exe ./data/input/slope.flt ./data/output/avgslope.flt
*/

#include<malloc.h>
#include<math.h>
#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include"utilities.h"

int *topovecind,*iup,*idown,*jup,*jdown;
float **arr,**topo,**acc,**area,*topovec,dx;
long Nx,Ny;

void setupgridneighbors()
{
    int i,j;
    for (i=1;i<=Ny;i++)
    {
        idown[i]=i-1;
        iup[i]=i+1;
    }
    for (j=1;j<=Nx;j++)
    {
        jdown[j]=j-1;
        jup[j]=j+1;
    }
    // open boundaries
    idown[1]=1;
    iup[Ny]=Ny;
    jdown[1]=1;
    jup[Nx]=Nx;
}

void allocatearrays()
{
    arr = matrix(1,Ny,1,Nx);
    area = matrix(1,Ny,1,Nx);
    topo = matrix(1,Ny,1,Nx);
    acc = matrix(1,Ny,1,Nx);
    topovec = vector(1,Ny*Nx);
    topovecind = ivector(1,Ny*Nx);
    idown=ivector(1,Ny);
    iup=ivector(1,Ny);
    jup=ivector(1,Nx);
    jdown=ivector(1,Nx);
}

void freearrays()
{
    free_matrix(arr,1,Ny,1,Nx);
    free_matrix(area,1,Ny,1,Nx);
    free_matrix(topo,1,Ny,1,Nx);
    free_matrix(acc,1,Ny,1,Nx);
    free_vector(topovec,1,Ny*Nx);
    free_ivector(idown,1,Ny);
    free_ivector(iup,1,Ny);
    free_ivector(jdown,1,Nx);
    free_ivector(jup,1,Nx);
}

void fillinpitsandflats(int i, int j)
{
    float min,fillincrement;

    fillincrement=0.01;
    if ((i>1)&&(j>1)&&(i<Ny)&&(j<Nx))
    {
        min=topo[i][j];
        if (topo[iup[i]][j]<min) min=topo[iup[i]][j];
        if (topo[idown[i]][j]<min) min=topo[idown[i]][j];
        if (topo[i][jup[j]]<min) min=topo[i][jup[j]];
        if (topo[i][jdown[j]]<min) min=topo[i][jdown[j]];
        if (topo[iup[i]][jup[j]]<min) min=topo[iup[i]][jup[j]];
        if (topo[idown[i]][jup[j]]<min) min=topo[idown[i]][jup[j]];
        if (topo[idown[i]][jdown[j]]<min) min=topo[idown[i]][jdown[j]];
        if (topo[iup[i]][jdown[j]]<min) min=topo[iup[i]][jdown[j]];
        if (topo[i][j]<=min)
        {
            // The node's a pit or flat, increment its elevation and push all neighbor nodes
            topo[i][j]=min+fillincrement;
            fillinpitsandflats(i,j);
            fillinpitsandflats(iup[i],j);
            fillinpitsandflats(idown[i],j);
            fillinpitsandflats(i,jup[j]);
            fillinpitsandflats(i,jdown[j]);
            fillinpitsandflats(iup[i],jup[j]);
            fillinpitsandflats(idown[i],jup[j]);
            fillinpitsandflats(idown[i],jdown[j]);
            fillinpitsandflats(iup[i],jdown[j]);
        }
    }
}

int calculated8drainagedirections(int i, int j)
{
    float down,oneoversqrt2;
    int flowdir;

    oneoversqrt2=0.707106781186; // diagonal neighbors are a distance of sqrt(2) further away then non-diagonals; therefore need to divide by sqrt(2)
    down=0.0;
    flowdir=0;
    if (oneoversqrt2*(topo[iup[i]][jdown[j]]-topo[i][j])<down)
    {
        down=oneoversqrt2*(topo[iup[i]][jdown[j]]-topo[i][j]);
        flowdir=1;
    }
    if (topo[iup[i]][j]-topo[i][j]<down)
    {
        down=(topo[iup[i]][j]-topo[i][j]);
        flowdir=2;
    }
    if (oneoversqrt2*(topo[iup[i]][jup[j]]-topo[i][j])<down)
    {
        down=oneoversqrt2*(topo[iup[i]][jup[j]]-topo[i][j]);
        flowdir=4;
    }
    if (topo[i][jup[j]]-topo[i][j]<down)
    {
        down=(topo[i][jup[j]]-topo[i][j]);
        flowdir=8;
    }
    if (oneoversqrt2*(topo[idown[i]][jup[j]]-topo[i][j])<down)
    {
        down=oneoversqrt2*(topo[idown[i]][jup[j]]-topo[i][j]);
        flowdir=16;
    }
    if (topo[idown[i]][j]-topo[i][j]<down)
    {
        down=(topo[idown[i]][j]-topo[i][j]);
        flowdir=32;
    }
    if (oneoversqrt2*(topo[idown[i]][jdown[j]]-topo[i][j])<down)
    {
        down=oneoversqrt2*(topo[idown[i]][jdown[j]]-topo[i][j]);
        flowdir=64;
    }
    if (topo[i][jdown[j]]-topo[i][j]<down)
    {
        down=(topo[i][jdown[j]]-topo[i][j]);
        flowdir=128;
    }
    return flowdir;
}

void flowaccumulated8(int i, int j)
{

    int flowdir;

    flowdir=calculated8drainagedirections(i,j);
    if (flowdir==0)
    {
        printf("Error: topographic pit detected! Input DEM must be hydrocorrected.\n");
        exit(EXIT_FAILURE);
    }

    if (flowdir==1)
    {
        acc[iup[i]][jdown[j]]+=acc[i][j];
        area[iup[i]][jdown[j]]+=area[i][j];
    }
    if (flowdir==2)
    {
        acc[iup[i]][j]+=acc[i][j];
        area[iup[i]][j]+=area[i][j];
    }
    if (flowdir==4)
    {
        acc[iup[i]][jup[j]]+=acc[i][j];
        area[iup[i]][jup[j]]+=area[i][j];
    }
    if (flowdir==8)
    {
        acc[i][jup[j]]+=acc[i][j];
        area[i][jup[j]]+=area[i][j];
    }
    if (flowdir==16)
    {
        acc[idown[i]][jup[j]]+=acc[i][j];
        area[idown[i]][jup[j]]+=area[i][j];
    }
    if (flowdir==32)
    {
        acc[idown[i]][j]+=acc[i][j];
        area[idown[i]][j]+=area[i][j];
    }
    if (flowdir==64)
    {
        acc[idown[i]][jdown[j]]+=acc[i][j];
        area[idown[i]][jdown[j]]+=area[i][j];
    }
    if (flowdir==128)
    {
        acc[i][jdown[j]]+=acc[i][j];
        area[i][jdown[j]]+=area[i][j];
    }
}

void flowrouting()
{
    int i,j,t;

    t=Nx*Ny+1;
    while (t>1)
    {
        t--;
        j=(topovecind[t])%Nx;
        if (j==0) j=Nx;
        i=(topovecind[t])/Nx+1;
        if (j==Nx) i--;
        if ((i>1)&&(i<Ny)&&(j>1)&&(j<Nx))  // check for NAN value
            flowaccumulated8(i,j);
    }
}

void normalizeupstreamsum()
{
    int i,j;

    for (i=1;i<=Ny;i++)
        for (j=1;j<=Nx;j++)
            if (topo[i][j]>0 && area[i][j]>0.1)
                acc[i][j] /= area[i][j];
}

int main(int argc, char *argv[])
{
    FILE *fr0,*fr1,*fw0;
    int i,j;

    // Set parameters of the input grid
    dx = 1.0;
    Nx = 200;
    Ny = 200;

    if (argc != 3)
    {
        printf("Error: two command line arguments required: 1) path to the array to be averaged; 2) path to the output file location.\n");
        exit(EXIT_FAILURE);
    }

    printf("Loading float accumulation array from: %s\n",argv[1]);
    printf("Writing output raster to: %s\n", argv[2]);

    // Open input files
    fr0 = fopen(argv[1], "rb"); fileerrorcheck(fr0);
    fr1 = fopen("./data/input/DEM.flt", "rb"); fileerrorcheck(fr1);

    // Array memory allocation
    allocatearrays();

    // Load data
    setupgridneighbors();
    for (i=1;i<=Ny;i++)
    {
        // Load  data from input files one row at a time; array pointers point to the first column of the i_th row
		(void) fread(&arr[i][1],sizeof(float),Nx,fr0);  // input to be averaged
        (void) fread(&topo[i][1],sizeof(float),Nx,fr1);  // digital elevation model (m)
    }
    fclose(fr0);fclose(fr1);
    
    // Hydrocorrection
    for (i=1;i<=Ny;i++)
        for (j=1;j<=Nx;j++)
            fillinpitsandflats(i,j);

    // Initialize remaining arrays
    for (i=1;i<=Ny;i++)
        for (j=1;j<=Nx;j++)
        {
            acc[i][j] = dx*dx*arr[i][j];
	        topovec[(i-1)*Nx+j]=topo[i][j];
            area[i][j]=dx*dx;  // contributing area (m^2)
        }

    // Sort the index table topovecind according to rank order of topography in topovec, lowest to highest
    indexx(Nx*Ny, topovec, topovecind);

    // Route flow
    flowrouting();

    // Normalize by drainage area
    normalizeupstreamsum();

    // Write accumulated raster to file
    fw0 = fopen(argv[2],"wb"); fileerrorcheck(fw0);
    for (i=1;i<=Ny;i++)
        (void) fwrite(&acc[i][1],sizeof(float),Nx,fw0);
    fclose(fw0);

    // Free array allocations
    freearrays();

    return 0;
}
