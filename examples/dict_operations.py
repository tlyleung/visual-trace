def dict_operations(scores: dict) -> int:
    total = 0
    for value in scores.values():
        total += value
    scores["d"] = total
    scores.clear()
    return total


def main():
    args = ({"a": 5, "b": 5, "c": 9},)
    func = dict_operations
    return func, args


if __name__ == "__main__":
    func, args = main()
    print(func(*args))
