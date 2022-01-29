from eldrow import constraint, ALPHA, given2, merge_constraints


def test_constraint():
    elims, cc = constraint('S(ES)an')
    assert len(elims) == 5
    assert cc['s'] == 2
    assert cc['e'] == 1
    assert ALPHA - elims[0] == set('s')
    assert elims[1] == set('aen')
    assert elims[2] == set('asn')

    elims, cc = constraint('S(LO)wS')
    assert len(elims) == 5
    assert cc['s'] == 2
    assert cc['l'] == 1
    assert cc['o'] == 1
    assert ALPHA - elims[0] == set('s')
    assert ALPHA - elims[4] == set('s')
    assert elims[1] == set('lw')
    assert elims[2] == set('ow')

    elims, cc = constraint('S(S)bsd')
    assert len(elims) == 5
    assert cc['s'] == 2
    assert elims[1] == set('sbd')
    assert elims[2] == set('bd')
    assert elims[3] == set('sbd')
    assert elims[4] == set('bd')


def test_gray_after_yellow():
    elims, cc = constraint('(P)pd')
    assert elims[0] == set('pd')
    assert elims[1] == set('pd')
    assert elims[2] == set('d')


def test_gray_after_green():
    elims, cc = constraint('Ppd')
    assert ALPHA - elims[0] == set('p')
    assert elims[1] == set('pd')
    assert elims[2] == set('pd')


def test_gray_before_green():
    elims, cc = constraint('pPd')
    assert elims[0] == set('pd')
    assert ALPHA - elims[1] == set('p')
    assert elims[2] == set('pd')


def test_yellow_before_green_before_gray():
    elims, cc = constraint('(B)Btb')
    assert elims[0] == set('bt')
    assert ALPHA - elims[1] == set('b')
    assert elims[2] == set('t')
    assert elims[3] == set('bt')
    assert cc['b'] == 2


def test_merge_constraints():
    elims, cc = merge_constraints(constraint('S(ES)an'), constraint('S(LO)wS'))
    assert cc['s'] == 2
    assert cc['l'] == 1
    assert cc['e'] == 1
    assert cc['o'] == 1
    assert len(cc) == 4
    assert ALPHA - elims[0] == set('s')
    assert ALPHA - elims[4] == set('s')
    assert elims[1] == set('elwan')
    assert elims[2] == set('sanow')
    assert elims[3] == set('anw')

    elims, cc = merge_constraints(constraint('S(ES)an'), constraint('S(LO)wS'), constraint('S(S)bsd'))
    assert cc['s'] == 2
    assert cc['l'] == 1
    assert cc['e'] == 1
    assert cc['o'] == 1
    assert len(cc) == 4
    assert ALPHA - elims[0] == set('s')
    assert elims[1] == set('elwanbsd')
    assert elims[2] == set('sanowbd')
    assert elims[3] == set('anwbsd')
    assert ALPHA - elims[4] == set('s')


def test_given2():
    p, c = given2("S(ES)an", "S(LO)wS")
    assert p == {0: {'s'}, 1: set('so'), 2: set('el'), 3: set('eols'), 4: {'s'}}, p

    p, c = given2("S(ES)an", "S(LO)wS", "S(S)bsd")  # this addition tells us there can only be two 's'
    assert p == {0: {'s'}, 1: {'o'}, 2: set('el'), 3: set('eol'), 4: {'s'}}, p


def test_can_matrix_solve_for_location_of_a_and_then_l():
    p, c = given2('s(LA)t(E)', 'p(A)vED')
    assert p == {0: {'a'}, 1: ALPHA - set('alpstv'), 2: {'l'}, 3: {'e'}, 4: {'d'}}, p


def test_can_matrix_solve_for_location_of_second_b():
    p, c = given2('(B)Btb')
    assert p[2] == set('b')
