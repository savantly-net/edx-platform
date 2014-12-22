# -*- coding: utf-8 -*-
"""
End-to-end tests for LibraryContent block in LMS
"""
import ddt

from ..helpers import UniqueCourseTest
from ...pages.studio.auto_auth import AutoAuthPage
from ...pages.studio.overview import CourseOutlinePage
from ...pages.studio.library import StudioLibraryContentXBlockEditModal, StudioLibraryContainerXBlockWrapper
from ...pages.lms.courseware import CoursewarePage
from ...pages.lms.library import LibraryContentXBlockWrapper
from ...pages.common.logout import LogoutPage
from ...fixtures.course import CourseFixture, XBlockFixtureDesc
from ...fixtures.library import LibraryFixture

SECTION_NAME = 'Test Section'
SUBSECTION_NAME = 'Test Subsection'
UNIT_NAME = 'Test Unit'


class LibraryContentTestBase(UniqueCourseTest):
    """ Base class for library content block tests """
    USERNAME = "STUDENT_TESTER"
    EMAIL = "student101@example.com"

    STAFF_USERNAME = "STAFF_TESTER"
    STAFF_EMAIL = "staff101@example.com"

    def populate_library_fixture(self, library_fixture):
        pass

    def setUp(self):
        """
        Set up library, course and library content XBlock
        """
        super(LibraryContentTestBase, self).setUp()

        self.courseware_page = CoursewarePage(self.browser, self.course_id)

        self.course_outline = CourseOutlinePage(
            self.browser,
            self.course_info['org'],
            self.course_info['number'],
            self.course_info['run']
        )

        self.library_fixture = LibraryFixture('test_org', self.unique_id, 'Test Library {}'.format(self.unique_id))
        self.populate_library_fixture(self.library_fixture)

        self.library_fixture.install()
        self.library_info = self.library_fixture.library_info
        self.library_key = self.library_fixture.library_key

        # Install a course with library content xblock
        self.course_fixture = CourseFixture(
            self.course_info['org'], self.course_info['number'],
            self.course_info['run'], self.course_info['display_name']
        )

        library_content_metadata = {
            'source_libraries': [self.library_key],
            'mode': 'random',
            'max_count': 1,
            'has_score': False
        }

        self.lib_block = XBlockFixtureDesc('library_content', "Library Content", metadata=library_content_metadata)

        self.course_fixture.add_children(
            XBlockFixtureDesc('chapter', SECTION_NAME).add_children(
                XBlockFixtureDesc('sequential', SUBSECTION_NAME).add_children(
                    XBlockFixtureDesc('vertical', UNIT_NAME).add_children(
                        self.lib_block
                    )
                )
            )
        )

        self.course_fixture.install()

    def _change_library_content_settings(self, count=1, capa_type=None):
        """
        Performs library block refresh in Studio, configuring it to show {count} children
        """
        unit_page = self._go_to_unit_page(True)
        library_container_block = StudioLibraryContainerXBlockWrapper.from_xblock_wrapper(unit_page.xblocks[0])
        modal = StudioLibraryContentXBlockEditModal(library_container_block.edit())
        modal.count = count
        if capa_type is not None:
            modal.capa_type = capa_type
        library_container_block.save_settings()
        self._go_to_unit_page(change_login=False)
        unit_page.wait_for_page()
        unit_page.publish_action.click()
        unit_page.wait_for_ajax()
        self.assertIn("Published and Live", unit_page.publish_title)

    @property
    def library_xblocks_texts(self):
        """
        Gets texts of all xblocks in library
        """
        return frozenset(child.data for child in self.library_fixture.children)

    def _go_to_unit_page(self, change_login=True):
        """
        Open unit page in Studio
        """
        if change_login:
            LogoutPage(self.browser).visit()
            self._auto_auth(self.STAFF_USERNAME, self.STAFF_EMAIL, True)
        self.course_outline.visit()
        subsection = self.course_outline.section(SECTION_NAME).subsection(SUBSECTION_NAME)
        return subsection.toggle_expand().unit(UNIT_NAME).go_to()

    def _goto_library_block_page(self, block_id=None):
        """
        Open library page in LMS
        """
        self.courseware_page.visit()
        block_id = block_id if block_id is not None else self.lib_block.locator
        #pylint: disable=attribute-defined-outside-init
        self.library_content_page = LibraryContentXBlockWrapper(self.browser, block_id)
        self.library_content_page.wait_for_page()

    def _auto_auth(self, username, email, staff):
        """
        Logout and login with given credentials.
        """
        AutoAuthPage(self.browser, username=username, email=email,
                     course_id=self.course_id, staff=staff).visit()


@ddt.ddt
class LibraryContentTest(LibraryContentTestBase):
    """
    Test courseware.
    """
    def populate_library_fixture(self, library_fixture):
        """
        Populates library fixture with XBlock Fixtures
        """
        library_fixture.add_children(
            XBlockFixtureDesc("html", "Html1", data='html1'),
            XBlockFixtureDesc("html", "Html2", data='html2'),
            XBlockFixtureDesc("html", "Html3", data='html3'),
        )

    @ddt.data(1, 2, 3)
    def test_shows_random_xblocks_from_configured(self, count):
        """
        Scenario: Ensures that library content shows {count} random xblocks from library in LMS
        Given I have a library, a course and a LibraryContent block in that course
        When I go to studio unit page for library content xblock as staff
        And I set library content xblock to display {count} random children
        And I refresh library content xblock and pulbish unit
        When I go to LMS courseware page for library content xblock as student
        Then I can see {count} random xblocks from the library
        """
        self._change_library_content_settings(count=count)
        self._auto_auth(self.USERNAME, self.EMAIL, False)
        self._goto_library_block_page()
        children_contents = self.library_content_page.children_contents
        self.assertEqual(len(children_contents), count)
        self.assertLessEqual(children_contents, self.library_xblocks_texts)

    def test_shows_all_if_max_set_to_greater_value(self):
        """
        Scenario: Ensures that library content shows {count} random xblocks from library in LMS
        Given I have a library, a course and a LibraryContent block in that course
        When I go to studio unit page for library content xblock as staff
        And I set library content xblock to display more children than library have
        And I refresh library content xblock and pulbish unit
        When I go to LMS courseware page for library content xblock as student
        Then I can see all xblocks from the library
        """
        self._change_library_content_settings(count=10)
        self._auto_auth(self.USERNAME, self.EMAIL, False)
        self._goto_library_block_page()
        children_contents = self.library_content_page.children_contents
        self.assertEqual(len(children_contents), 3)
        self.assertEqual(children_contents, self.library_xblocks_texts)


@ddt.ddt
class StudioLibraryContainerCapaFilterTest(LibraryContentTestBase):
    """
    Test Library Content block in LMS
    """
    def _get_problem_choice_group_text(self, name, items):
        """ Generates Choice Group CAPA problem XML """
        items_text = "\n".join([
            "<choice correct='{correct}'>{item}</choice>".format(correct=correct, item=item)
            for item, correct in items
        ])

        return """<problem>
    <p>{name}</p>
    <multiplechoiceresponse>
        <choicegroup label="{name}" type="MultipleChoice">{items}</choicegroup>
    </multiplechoiceresponse>
</problem>""".format(name=name, items=items_text)

    def _get_problem_select_text(self, name, items, correct):
        """ Generates Select Option CAPA problem XML """
        items_text = ",".join(map(lambda item: "'{0}'".format(item), items))

        return """<problem>
<p>{name}</p>
<optionresponse>
  <optioninput label="{name}" options="({options})" correct="{correct}"></optioninput>
</optionresponse>
</problem>""".format(name=name, options=items_text, correct=correct)

    def populate_library_fixture(self, library_fixture):
        """
        Populates library fixture with XBlock Fixtures
        """
        library_fixture.add_children(
            XBlockFixtureDesc(
                "problem", "Problem Choice Group 1",
                data=self._get_problem_choice_group_text("Problem Choice Group 1 Text", [("1", False), ('2', True)])
            ),
            XBlockFixtureDesc(
                "problem", "Problem Choice Group 2",
                data=self._get_problem_choice_group_text("Problem Choice Group 2 Text", [("Q", True), ('W', False)])
            ),
            XBlockFixtureDesc(
                "problem", "Problem Select 1",
                data=self._get_problem_select_text("Problem Select 1 Text", ["Option 1", "Option 2"], "Option 1")
            ),
            XBlockFixtureDesc(
                "problem", "Problem Select 2",
                data=self._get_problem_select_text("Problem Select 2 Text", ["Option 3", "Option 4"], "Option 4")
            ),
        )

    @property
    def _problem_headers(self):
        """ Expected XBLock headers according to populate_library_fixture """
        return frozenset(child.display_name.upper() for child in self.library_fixture.children)

    @ddt.data(1, 3)
    def test_any_capa_type_shows_all(self, count):
        """
        Scenario: Ensure setting "Any Type" for Problem Type does not filter out Problems
        Given I have a library with two "Select Option" and two "Choice Group" problems, and a course containing
               LibraryContent XBlock configured to draw XBlocks from that library
        When I go to studio unit page for library content xblock as staff
        And I set library content xblock Problem Type to "Any Type" and Count to {count}
        And I refresh library content xblock and pulbish unit
        When I go to LMS courseware page for library content xblock as student
        Then I can see {count} xblocks from the library of any type
        """
        self._change_library_content_settings(count=count, capa_type="Any Type")
        self._auto_auth(self.USERNAME, self.EMAIL, False)
        self._goto_library_block_page()
        children_headers = self.library_content_page.children_headers
        self.assertEqual(len(children_headers), count)
        self.assertLessEqual(children_headers, self._problem_headers)

    @ddt.data(
        ('Choice Group', 1, ["Problem Choice Group 1", "Problem Choice Group 2"]),
        ('Select Option', 2, ["Problem Select 1", "Problem Select 2"]),
    )
    @ddt.unpack
    def test_capa_type_shows_only_chosen_type(self, capa_type, count, expected_headers):
        """
        Scenario: Ensure setting "{capa_type}" for Problem Type draws aonly problem of {capa_type} from library
        Given I have a library with two "Select Option" and two "Choice Group" problems, and a course containing
               LibraryContent XBlock configured to draw XBlocks from that library
        When I go to studio unit page for library content xblock as staff
        And I set library content xblock Problem Type to "{capa_type}" and Count to {count}
        And I refresh library content xblock and pulbish unit
        When I go to LMS courseware page for library content xblock as student
        Then I can see {count} xblocks from the library of {capa_type}
        """
        self._change_library_content_settings(count=count, capa_type=capa_type)
        self._auto_auth(self.USERNAME, self.EMAIL, False)
        self._goto_library_block_page()
        children_headers = self.library_content_page.children_headers
        self.assertEqual(len(children_headers), count)
        self.assertLessEqual(children_headers, self._problem_headers)
        self.assertLessEqual(children_headers, set(map(lambda header: header.upper(), expected_headers)))

    def test_missing_capa_type_shows_none(self):
        """
        Scenario: Ensure setting "{capa_type}" for Problem Type that is not present in library results in empty XBlock
        Given I have a library with two "Select Option" and two "Choice Group" problems, and a course containing
               LibraryContent XBlock configured to draw XBlocks from that library
        When I go to studio unit page for library content xblock as staff
        And I set library content xblock Problem Type to type not present in library
        And I refresh library content xblock and pulbish unit
        When I go to LMS courseware page for library content xblock as student
        Then I can see no xblocks
        """
        self._change_library_content_settings(count=1, capa_type="Matlab")
        self._auto_auth(self.USERNAME, self.EMAIL, False)
        self._goto_library_block_page()
        children_headers = self.library_content_page.children_headers
        self.assertEqual(len(children_headers), 0)
