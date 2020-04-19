# Python3 code to demonstrate
# generating random strings
# using random.choices()
import string
import random

# initializing size of string
N = 7

# using random.choices()
# generating random strings
for i in range(10):
    print(''.join(random.choices(string.ascii_uppercase +
                                 string.digits, k=N)))
