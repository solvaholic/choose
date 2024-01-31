#!/usr/bin/python3
#
# An interactive shell script to help user choose between N options.
#
# Usage: choose.py

# Prompt user for a comma-separated list of options.
# TODO: Validate input.
# TODO: Also receive options as arguments, or by stdin.
# TODO: Allow for other separators.
def read_options():
    options = input("Enter a comma-separated list of options: ")
    return options.split(", ")

# For each option, ask whether user prefers this option or each of
# the other options. Do not repeat comparisons. Remember user's
# preferences so they can be used used as a tie-breaker.
# TODO: Validate input.
# TODO: Simplify input, e.g. "1" for first option, "2" for second.
def eval_options(options):
    import itertools
    preferences = {}
    for option1, option2 in itertools.combinations(options, 2):
        response = input("Would you rather %s or %s? " % (option1, option2))
        preferences[(option1, option2)] = response
    return preferences

# Rank options by count of how many times each was preferred over
# others.
# TODO: Solve ties here, or in output?
def rank_options(options, preferences):
    import collections
    counts = collections.Counter()
    for (option1, option2), preference in preferences.items():
        if preference == option1:
            counts[option1] += 1
        else:
            counts[option2] += 1
    return counts

# Output each ranked option and its preference count. Sort output by
# preference count.
# TODO: Solve ties here, or in ranking?
def print_ranked_options(ranked_options):
    for option, count in sorted(ranked_options.items(), key=lambda x: (-x[1], x[0])):
        print("%s: %d" % (option, count))

def main():
    options = read_options()
    preferences = eval_options(options)
    ranked_options = rank_options(options, preferences)
    print_ranked_options(ranked_options)

if __name__ == "__main__":
    main()
