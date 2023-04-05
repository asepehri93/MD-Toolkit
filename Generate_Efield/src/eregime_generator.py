import sys
import math
import argparse

def generate_eregime_in(max_magnitude, step_angle, iteration_step, num_cycles):
    num_points = int(round((2 * num_cycles * math.pi) / step_angle)) + 1
    with open("eregime.in", "w") as f:
        f.write("#Electric field regimes\n")
        f.write("#start #V direction1 Magnitude1(V/A) direction2 Magnitude2(V/A)\n")
        for i in range(num_points):
            angle = i * step_angle
            magnitude = max_magnitude * math.sin(angle)
            f.write(f"{i*iteration_step:6d}     1        z              {magnitude: .4f}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a sinusoidal electric field regime file (eregime.in) based on the input parameters.")
    parser.add_argument("max_magnitude", type=float, help="The maximum magnitude of the sinusoidal electric field.")
    parser.add_argument("step_angle", type=float, help="The step angle in radians for generating the sinusoidal data.")
    parser.add_argument("iteration_step", type=int, help="The iteration step between data points in the output file.")
    parser.add_argument("num_cycles", type=float, help="The number of sine cycles.") 
    args = parser.parse_args()

    generate_eregime_in(args.max_magnitude, args.step_angle, args.iteration_step)
