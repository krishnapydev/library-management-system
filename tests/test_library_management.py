from library_management import LibraryManagementSystem


def test_lend_and_return_without_reservation():
    lib = LibraryManagementSystem()
    book_id = lib.add_book("Clean Code")
    member_id = lib.add_member("Alice")

    assert lib.lend_book(book_id, member_id) is True
    assert lib.lend_book(book_id, member_id) is False

    assigned = lib.return_book(book_id, member_id)
    assert assigned is None
    assert lib.lend_book(book_id, member_id) is True



def test_reservations_are_fifo_on_return():
    lib = LibraryManagementSystem()
    book_id = lib.add_book("Design Patterns")
    first_member = lib.add_member("Bob")
    second_member = lib.add_member("Carol")
    borrower = lib.add_member("Dave")

    assert lib.lend_book(book_id, borrower) is True
    assert lib.reserve_book(book_id, first_member) is True
    assert lib.reserve_book(book_id, second_member) is True

    assigned = lib.return_book(book_id, borrower)
    assert assigned == first_member



def test_recent_actions_are_lifo():
    lib = LibraryManagementSystem()
    book_id = lib.add_book("Refactoring")
    member_id = lib.add_member("Eve")

    lib.reserve_book(book_id, member_id)
    lib.lend_book(book_id, member_id)

    assert lib.pop_recent_action() == f"lend:{book_id}:{member_id}"
    assert lib.pop_recent_action() == f"reserve:{book_id}:{member_id}"
    assert lib.pop_recent_action() is None
