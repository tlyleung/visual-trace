from visual_trace.data_structures.list import List


def max_sub_array(nums: List[int]) -> int:
    ans = float("-inf")
    curr = float("-inf")
    for num in nums:
        curr = max(curr + num, num)
        ans = max(ans, curr)
    return ans


def main():
    # args = (List(-2, 1, -3, 4, -1, 2, 1, -5, 4),)
    args = (List(-2, 1),)
    func = max_sub_array
    return func, args


if __name__ == "__main__":
    func, args = main()
    print(func(*args))
