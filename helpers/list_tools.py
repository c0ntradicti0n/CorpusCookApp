def find_repeating(lst, count=2):
    ret = []
    counts = [None] * len(lst)
    for i in lst:
        if counts[i] is None:
            counts[i] = i
        elif i == counts[i]:
            ret += [i]
            if len(ret) == count:
                return ret