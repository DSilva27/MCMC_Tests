import scipy
from scipy import stats
from scipy import interpolate
from scipy.special import logsumexp
import numpy as np
from numpy.random import random
import matplotlib.pyplot as plt
import seaborn as sns


def gen_images(n_images, centers, sigma):
    '''
    Function to generate the synthetic data to be used in MCMC. The data is distributed as double-well potential.
    We select a random value between x1 and x2 (centers) and apply Gaussian noise around said value.
    
    Input:
          n_images: number of images to be created
          centers: centers of the double-well potential
          sigma: standard deviation of the gaussian noise needed to create the data
    
    Output:
          dataset: numpy array with the generated data
    '''
    
    print(f"Generating {n_images} Images...")
    dataset = np.zeros(n_images)

    for i in range(n_images):

        k = np.random.randint(0, centers.size) # Select a cente r
        dataset[i] = np.random.normal(centers[k], sigma) #apply Gaussian noise and save the "image"

    print("... done")
    return dataset

def energy_em(X, images, sigma=1, kT=1):
    '''
    Function that calculates the energy as kbT * negative log-likelihood.
    The likelihood of observing an image given two models is defined as L(w|{x1,x2}) = \sum_j=1,2 0.5 * N(w | x_j, sigma)
    The total likelihood is defined as \prod_w L(w | {x1, x2}) 
    
    Input: X: the two configurations x1 and x2
           images: dataset (synthetic data generated by gen_images(...))
           sigma: parameter for the likelihood
           kT: temperature of the system
    '''

    energy = -kT * np.sum(logsumexp(0.5 * np.exp(-(X[:, None] - images)**2 / (2 * sigma**2)), axis=0))
    return energy

# Prior distribution for mcmc. Simply a gaussian centered around zero and wide enough to cover the two centers of the double-well
prior = lambda x, sigma, kT: kT * 0.5 * (x / sigma)**2

def do_mcmc(steps, images, x0, sigma=1, kT=1):
    '''
    Multiple walkers mcmc to find the two structures hidden in images
    '''
    
    #do step 0
    x = x0
    samples = np.zeros((steps, 2))
    samples[0] = x
    
    #save the old energy
    old_e = p_em(x, images, sigma, kT) 

    #print(f"Starting MCMC")
    #print("accepted x xp p(x) p(xp)")

    # do the rest of the steps
    c = 1
    for _ in range(1, steps):
        
        # Generate a displacement for each proposed
        dx = np.random.normal(0, 0.1, 2)
        x1 = x[0] + dx[0]
        x2 = x[1] + dx[1]
        
        # Calculate the acceptance ratio for each replica
        a1 = p_em(np.array([x1, x[1]]), images, sigma, kT) - old_e - prior(x1, 3, kT) + prior(x[0], 3, kT) 
        a2 = p_em(np.array([x[0], x2]), images, sigma, kT) - old_e - prior(x2, 3, kT) + prior(x[1], 3, kT)
        
        # Probability of acceptance 
        p_a = -np.log(np.random.rand(2))
        
        # Accept or reject the displacements
        
        # Both displacements are accepted
        if a1 < 0 and a2 < 0:

            x = np.array([x1, x2])
            samples[c] = x
            old_e = p_em(x, images, sigma, kT)
            c += 1
        
        # Both displacements can be accepted, though it is possible to accept only one
        elif a1 < 0 and a2 > 0:

            if a2 < p_a[1]:

                x = np.array([x1, x2])
                samples[c] = x
                old_e = p_em(x, images, sigma, kT)
                c += 1

            else: 

                x = np.array([x1, x[1]])
                samples[c] = x
                old_e = p_em(x, images, sigma, kT)
                c += 1

        elif a1 > 0 and a2 < 0:

            if a1 < p_a[0]:

                x = np.array([x1, x2])
                samples[c] = x
                old_e = p_em(x, images, sigma, kT)
                c += 1

            else: 

                x = np.array([x[0], x2])
                samples[c] = x
                old_e = p_em(x, images, sigma, kT)
                c += 1

        elif a1 > 0 and a2 > 0:

            if a1 < p_a[0] and a2 < p_a[1]: 

                x = np.array([x1, x2])
                samples[c] = x
                old_e = p_em(x, images, sigma, kT)
                c += 1

            elif a1 < p_a[0] and a2 > p_a[1]:

                x = np.array([x1, x[1]])
                samples[c] = x
                old_e = p_em(x, images, sigma, kT)
                c += 1
                
            elif a1 > p_a[0] and a2 < p_a[1]:

                x = np.array([x[0], x2])
                samples[c] = x
                old_e = p_em(x, images, sigma, kT)
                c += 1

            else:
                #print(f"0 {x} {xp} {p_em(x, images)} {p_em(xp, images)}")
                continue     
    
    # if (c < tot_samp):
    #     print(f"Max Iterations reached: total samples = {c}")

    return samples[:c, :]


def p_to_fes(p, grid, kT=2.494339):

    fes = p.copy()
    fes[np.where(fes < 0.01)] = float("nan")

    fes = -kT * np.log(fes)
    fes -= np.nanmin(fes)

    return fes

# Ignore this functions, I will comment and polish them later

def gen_fes(samples, grid, kT=2.494339):

    kernel = stats.gaussian_kde(samples)

    y = kernel(grid)
    y[np.where(y < 0.01)] = float("nan")

    y = -kT * np.log(y)
    y -= np.nanmin(y)

    return y


def compare_dist(grid, ref, dist1, dist2):

    ref_fes = gen_fes(ref, grid)
    dist1_fes = gen_fes(dist1, grid)
    dist2_fes = gen_fes(dist2, grid)

    plt.plot(grid, ref_fes, color="black", label="ref")
    plt.plot(grid, dist1_fes, ls=":", color="orange", label="OR")
    #plt.plot(grid, dist2_fes, ls="--", color="blue", label="AND")

    plt.xlabel("Intensity [I]")
    plt.ylabel("FES [kJ / mol")
    plt.legend()

    plt.show()

def compare_hist(grid, ref, dist1, dist2):

    ref_kernel = stats.gaussian_kde(ref)
    dist1_kernel = stats.gaussian_kde(dist1)
    dist2_kernel = stats.gaussian_kde(dist2)

    kde_ref = ref_kernel(grid)
    kde_ref -= np.nanmin(kde_ref)
    kde_ref /= np.nanmax(kde_ref)

    kde_dist1 = dist1_kernel(grid)
    kde_dist1 -= np.nanmin(kde_dist1)
    kde_dist1 /= np.nanmax(kde_dist1)

    kde_dist2 = dist2_kernel(grid)
    kde_dist2 -= np.nanmin(kde_dist2)
    kde_dist2 /= np.nanmax(kde_dist2)

    plt.hist(ref, bins=50, color="black", label="ref", histtype="step",   cumulative=False, density=False,)
    plt.hist(dist1, bins=50, color="orange", label="OR", histtype="step", cumulative=False, density=False)
    plt.hist(dist2, bins=50, color="blue", label="AND", histtype="step",  cumulative=False, density=False)

    # plt.plot(grid, kde_ref, color="black", label="ref")
    # plt.plot(grid, kde_dist1, ls=":", color="orange", label="OR")
    # plt.plot(grid, kde_dist2, ls="--", color="blue", label="AND")

    plt.xlabel("Intensity [I]")
    #plt.ylabel("FES [kJ / mol")
    plt.legend()

    plt.show()


def main():
  
    #np.random.seed(0)
    x1 = -2
    x2 = 2
    x = np.array([x1, x2])
    #x = np.random.normal(0, 2, 2)

    images = gen_images(10000, x, 2)
    #xo = np.random.normal(0, 2, 2)
    xo = np.array([-3, 1])

    # samp = do_mcmc(10000, images, xo, kT=1)
    # np.save("samp.npy", samp)
    # np.save("images.npy", images)

    images = np.load("images.npy")
    samp = np.load("samp.npy")#.flatten()

    print(samp)

    plt.hist(samp[:, 0])
    plt.hist(samp[:, 1])
    plt.show()

    # grid = np.linspace(-3, 3, 100)
    # img_fes = gen_fes(images, grid, kT=1)

    # plt.plot(grid, img_fes)
    # plt.show()
    # compare_dist(GRID, images, samp_OR, samp_AND)
    # compare_hist(GRID, images, samp_OR, samp_AND)
    
    return 0

if __name__ == "__main__":
      
    main()
