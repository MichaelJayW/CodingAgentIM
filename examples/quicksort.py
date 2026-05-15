"""Quick Sort implementation."""


def quicksort(arr: list) -> list:
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)


if __name__ == "__main__":
    data = [38, 27, 43, 3, 9, 82, 10]
    print(f"原始: {data}")
    print(f"排序: {quicksort(data)}")
