test = ['a','b',2,'d',2,'f']
blist = [True, False, True, False, False, True]

new = []
for i, b in enumerate(blist):
    if b:
        new.append(test[i])
print(new)

print(sum(m == 2 for m in test))