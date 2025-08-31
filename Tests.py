seats = [1,2,3,4,5,6,7,8,9]
n_seats = len(seats)

bu_seat = 1
sb_seat = 8
bb_seat = 5

if bu_seat < sb_seat:
    between_bu_and_sb_inclusive = seats[bu_seat:sb_seat]
elif bu_seat > sb_seat:
    between_bu_and_sb_inclusive = seats[:sb_seat] + seats[bu_seat:]
else:
    raise RuntimeError("Button cannot be the Big Blind")

print(between_bu_and_sb_inclusive)
print(seats[1:4])