from visual_trace.data_structures.dict import Dict
from visual_trace.data_structures.list import List


def two_sum(nums: List[int], target: int) -> List[int]:
    d = Dict()

    for i in range(len(nums)):
        num = nums[i]

        if target - num in d:
            return d[target - num], i
        else:
            d[num] = i


def main():
    args = (List(2, 7, 11, 15), 9)
    func = two_sum
    return func, args


if __name__ == "__main__":
    func, args = main()
    print(func(*args))
