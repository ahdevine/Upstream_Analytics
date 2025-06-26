/*
 computes drainage area from a DEM

 expects input DEM at ./data/input/DEM.flt
 writes output contributing area raster to ./data/input/contribarea.flt  (this is where upstreamavg.c will expect it)

 compile with:
    gcc -o drainagearea.exe drainagearea.c utilities.c -lm
 run with:
    ./drainagearea.exe
*/

#include<malloc.h>
#include<math.h>
#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include"utilities.h"


int *topovecind,*iup,*idown,*jup,*jdown;
float **topo,**area,*topovec,dx;
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
    area = matrix(1,Ny,1,Nx);
    topo = matrix(1,Ny,1,Nx);
    topovec = vector(1,Ny*Nx);
    topovecind = ivector(1,Ny*Nx);
    idown=ivector(1,Ny);
    iup=ivector(1,Ny);
    jup=ivector(1,Nx);
    jdown=ivector(1,Nx);
}

void freearrays()
{
    free_matrix(area,1,Ny,1,Nx);
    free_matrix(topo,1,Ny,1,Nx);
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
        area[iup[i]][jdown[j]]+=area[i][j];
    if (flowdir==2)
        area[iup[i]][j]+=area[i][j];
    if (flowdir==4)
        area[iup[i]][jup[j]]+=area[i][j];
    if (flowdir==8)
        area[i][jup[j]]+=area[i][j];
    if (flowdir==16)
        area[idown[i]][jup[j]]+=area[i][j];
    if (flowdir==32)
        area[idown[i]][j]+=area[i][j];
    if (flowdir==64)
        area[idown[i]][jdown[j]]+=area[i][j];
    if (flowdir==128)
        area[i][jdown[j]]+=area[i][j];
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
        if ((i>1)&&(i<Ny)&&(j>1)&&(j<Nx))
            flowaccumulated8(i,j);
    }
}

int main(int argc, char *argv[])
{
    FILE *fr0,*fw0;
    int i,j;

    // Set parameters of the input grid
    dx = 1.0;
    Nx = 200;
    Ny = 200;

    // Open input files
    fr0 = fopen("./data/input/DEM.flt", "rb"); fileerrorcheck(fr0);

    // Array memory allocation
    allocatearrays();

    // Load data
    setupgridneighbors();
    for (i=1;i<=Ny;i++)
        (void) fread(&topo[i][1],sizeof(float),Nx,fr0);  // digital elevation model (m)
    fclose(fr0);
    
    // Hydrocorrection
    for (i=1;i<=Ny;i++)
        for (j=1;j<=Nx;j++)
            fillinpitsandflats(i,j);

    // Initialize remaining arrays
    for (i=1;i<=Ny;i++)
        for (j=1;j<=Nx;j++)
        {
            area[i][j]=dx*dx;
	        topovec[(i-1)*Nx+j]=topo[i][j];
        }

    // Sort the index table topovecind according to rank order of topography in topovec, lowest to highest
    indexx(Nx*Ny, topovec, topovecind);

    // Route flow
    flowrouting();

    // Write contributing area raster to file (write to data/input/ because that's where upstreamavg.c expects it)
    fw0 = fopen("./data/input/contribarea.flt","wb"); fileerrorcheck(fw0);
    for (i=1;i<=Ny;i++)
        (void) fwrite(&area[i][1],sizeof(float),Nx,fw0);
    fclose(fw0);

    // Free array allocations
    freearrays();

    return 0;
}
