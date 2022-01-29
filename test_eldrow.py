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

    p, c = given2('s(LA)t(E)', 'p(A)vED')
    assert p == {0: {'a'}, 1: ALPHA - set('alpstv'), 2: {'l'}, 3: {'e'}, 4: {'d'}}, p
