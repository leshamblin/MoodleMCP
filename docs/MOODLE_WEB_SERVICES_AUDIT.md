# Comprehensive Moodle Web Services API Audit

This document provides a complete audit of all major Moodle Web Services API functions across all core modules and activity modules. Use this as a reference for implementing comprehensive Moodle integration.

**Legend:**
- ✅ **READ** - Read-only operation (safe, idempotent)
- ⚠️ **WRITE** - Modifies data (requires appropriate permissions)
- 🔑 **REQUIRES** - Special parameters or permissions noted

---

## 1. CORE_COURSE Module - Course Management

### Course CRUD Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_course_create_courses` | ⚠️ WRITE | Create new courses | courses[] (shortname, fullname, categoryid) | summary, format, showgrades, startdate, enddate, etc. | 🔑 Requires moodle/course:create |
| `core_course_update_courses` | ⚠️ WRITE | Update existing courses | courses[] (id + fields to update) | Any course field | 🔑 Requires course_id, moodle/course:update |
| `core_course_delete_courses` | ⚠️ WRITE | Delete courses | courseids[] | None | 🔑 DESTRUCTIVE, requires moodle/course:delete |
| `core_course_duplicate_course` | ⚠️ WRITE | Duplicate a course | courseid, fullname, shortname, categoryid | visible, options[] | 🔑 Creates new course, requires course_id |
| `core_course_import_course` | ⚠️ WRITE | Import content from another course | importfrom (course_id), importto (course_id) | deletecontent, options[] | 🔑 Requires both source and target course_id |

### Course Information (READ)

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_course_get_courses` | ✅ READ | Get course details by ID | options[ids][] | None | Returns full course objects |
| `core_course_get_courses_by_field` | ✅ READ | Get courses by field match | field, value | None | 🔑 Supports: id, ids, shortname, idnumber, category, sectionid |
| `core_course_search_courses` | ✅ READ | Search courses | criterianame, criteriavalue | page, perpage, requiredcapabilities[], limittoenrolled | Returns matching courses |
| `core_course_get_contents` | ✅ READ | Get course structure/modules | courseid | options[] (excludemodules, excludecontents, etc.) | Returns sections with modules |
| `core_course_get_course_module` | ✅ READ | Get specific module details | cmid | None | 🔑 Requires course module ID |
| `core_course_get_course_module_by_instance` | ✅ READ | Get module by instance ID | module (name), instance (id) | None | e.g., module='forum', instance=123 |
| `core_course_get_recent_courses` | ✅ READ | Get recently accessed courses | userid | limit, offset, sort | Returns courses sorted by access |
| `core_course_get_enrolled_courses_by_timeline_classification` | ✅ READ | Get courses by timeline | classification, limit | offset, sort, customfieldname, customfieldvalue | 🔑 classification: all, inprogress, future, past |
| `core_course_get_categories` | ✅ READ | Get course categories | None | criteria[] (id, name, parent, etc.), addsubcategories | Returns category tree |
| `core_course_get_updates_since` | ✅ READ | Get course updates since timestamp | courseid, since | filter[] | Track changes since date |
| `core_course_view_course` | ✅ READ | Log course view | courseid | sectionnumber | Triggers view event |

### Course Categories

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_course_create_categories` | ⚠️ WRITE | Create course categories | categories[] (name, parent) | description, descriptionformat, theme, idnumber | 🔑 Requires moodle/category:manage |
| `core_course_update_categories` | ⚠️ WRITE | Update categories | categories[] (id + fields) | name, parent, description, etc. | 🔑 Requires category_id |
| `core_course_delete_categories` | ⚠️ WRITE | Delete categories | categories[] (id) | recursive, newparent | 🔑 DESTRUCTIVE operation |

---

## 2. CORE_USER Module - User Management

### User CRUD Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_user_create_users` | ⚠️ WRITE | Create new users | users[] (username, password, firstname, lastname, email) | auth, city, country, timezone, customfields[], preferences[] | 🔑 Requires moodle/user:create |
| `core_user_update_users` | ⚠️ WRITE | Update user details | users[] (id + fields to update) | username, email, firstname, lastname, customfields[], preferences[] | 🔑 Requires user_id |
| `core_user_delete_users` | ⚠️ WRITE | Delete users | userids[] | None | 🔑 DESTRUCTIVE, requires moodle/user:delete |

### User Information (READ)

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_user_get_users_by_field` | ✅ READ | Get users by field | field, values[] | None | 🔑 field: id, idnumber, username, email |
| `core_user_get_users` | ✅ READ | Search users by criteria | criteria[] (key, value) | None | Search by: firstname, lastname, email, id, etc. |
| `core_user_get_course_user_profiles` | ✅ READ | Get user profiles in course | userlist[] (userid, courseid) | None | Returns user info + course-specific data |
| `core_user_get_user_preferences` | ✅ READ | Get user preferences | None (current user) | name, userid | Returns preference key-value pairs |
| `core_user_update_user_preferences` | ⚠️ WRITE | Update user preferences | preferences[] (type, value) | userid | Set user settings |
| `core_user_update_user_device_public_key` | ⚠️ WRITE | Update device public key | uuid, appid, publickey | None | For mobile app authentication |
| `core_user_add_user_device` | ⚠️ WRITE | Register user device | appid, name, model, platform, version, pushid, uuid | None | Mobile device registration |
| `core_user_remove_user_device` | ⚠️ WRITE | Remove user device | uuid | appid | Unregister mobile device |
| `core_user_view_user_list` | ✅ READ | Log viewing user list | courseid | None | Triggers list view event |
| `core_user_view_user_profile` | ✅ READ | Log viewing user profile | userid | courseid | Triggers profile view event |
| `core_user_get_private_files_info` | ✅ READ | Get private files info | userid | None | Returns file area information |
| `core_user_agree_site_policy` | ⚠️ WRITE | Accept site policy | None | None | Mark policy as accepted |

---

## 3. CORE_ENROL Module - Enrollment Management

### Enrollment Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `enrol_manual_enrol_users` | ⚠️ WRITE | Manually enroll users | enrolments[] (roleid, userid, courseid) | timestart, timeend, suspend | 🔑 Requires course_id, user_id, role_id |
| `enrol_manual_unenrol_users` | ⚠️ WRITE | Manually unenroll users | enrolments[] (userid, courseid) | roleid | 🔑 Requires course_id, user_id |
| `core_enrol_get_enrolled_users` | ✅ READ | Get enrolled users in course | courseid | options[] (withcapability, groupid, onlyactive, etc.) | Returns user list with roles |
| `core_enrol_get_enrolled_users_with_capability` | ✅ READ | Get users with specific capability | courseid, capabilities[] | options[] (groupid, onlyactive, etc.) | Filter by capability |
| `core_enrol_get_users_courses` | ✅ READ | Get user's enrolled courses | userid | returnusercount | Returns course enrollment details |
| `core_enrol_get_course_enrolment_methods` | ✅ READ | Get enrollment methods | courseid | None | Returns enabled enrol plugins |
| `core_enrol_get_enrolled_users_by_timemodified` | ✅ READ | Get recently enrolled users | courseid, timemodifiedfrom | timemodifiedto | Track enrollment changes |
| `core_enrol_search_users` | ✅ READ | Search users for enrollment | courseid, search | searchanywhere, page, perpage | Returns enrollable users |
| `core_enrol_submit_user_enrolment_form` | ⚠️ WRITE | Edit user enrollment | formdata | None | Update enrollment details (Moodle 3.8+) |
| `core_enrol_unenrol_user_enrolment` | ⚠️ WRITE | Unenroll user | ueid | None | 🔑 Requires user enrollment ID |
| `enrol_self_enrol_user` | ⚠️ WRITE | Self-enroll in course | courseid | password, instanceid | User enrolls themselves |
| `enrol_self_get_instance_info` | ✅ READ | Get self-enrollment info | instanceid | None | Check if self-enrollment available |

---

## 4. CORE_CALENDAR Module - Calendar & Events

### Calendar Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_calendar_create_calendar_events` | ⚠️ WRITE | Create calendar events | events[] (name, timestart, eventtype) | description, courseid, groupid, userid, timeduration, etc. | 🔑 eventtype: user, group, course, site |
| `core_calendar_delete_calendar_events` | ⚠️ WRITE | Delete calendar events | events[] (eventid, repeat) | None | 🔑 Can delete repeating events |
| `core_calendar_update_event_start_day` | ⚠️ WRITE | Move event to different day | eventid, daytimestamp | None | Change event date |
| `core_calendar_get_calendar_events` | ✅ READ | Get calendar events | None | events[eventids][], events[courseids][], events[groupids][], options[] | Filter by IDs or date range |
| `core_calendar_get_action_events_by_timesort` | ✅ READ | Get action events sorted | timesortfrom | timesortto, limitnum, limittononsuspendedevents, userid, searchvalue | Events requiring action |
| `core_calendar_get_action_events_by_course` | ✅ READ | Get action events by course | courseid | timesortfrom, timesortto, searchvalue | Course-specific events |
| `core_calendar_get_action_events_by_courses` | ✅ READ | Get action events for multiple courses | courseids[], timesortfrom | timesortto, limitnum, searchvalue | Multiple courses |
| `core_calendar_get_calendar_upcoming_view` | ✅ READ | Get upcoming events view | None | courseid, categoryid | Upcoming deadlines |
| `core_calendar_get_calendar_monthly_view` | ✅ READ | Get monthly calendar view | year, month | courseid, categoryid, day | Month view data |
| `core_calendar_get_calendar_day_view` | ✅ READ | Get day calendar view | year, month, day | courseid, categoryid | Single day events |
| `core_calendar_get_calendar_access_information` | ✅ READ | Get calendar access info | courseid | None | User's calendar permissions |
| `core_calendar_get_allowed_event_types` | ✅ READ | Get allowed event types | courseid | None | What event types user can create |
| `core_calendar_get_calendar_event_by_id` | ✅ READ | Get single event by ID | eventid | None | Detailed event information |
| `core_calendar_submit_create_update_form` | ⚠️ WRITE | Submit calendar form | formdata | None | Create/update via form data |

---

## 5. CORE_MESSAGE Module - Messaging System

### Message Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_message_send_instant_messages` | ⚠️ WRITE | Send instant messages | messages[] (touserid, text) | None | 🔑 Requires recipient user_id |
| `core_message_send_messages_to_conversation` | ⚠️ WRITE | Send message to conversation | conversationid, messages[] (text) | None | 🔑 Requires conversation_id |
| `core_message_delete_message` | ⚠️ WRITE | Delete message | messageid, userid | read | Delete for current user |
| `core_message_delete_message_for_all_users` | ⚠️ WRITE | Delete message for everyone | messageid, userid | None | 🔑 DESTRUCTIVE, deletes for all |
| `core_message_delete_conversations_by_id` | ⚠️ WRITE | Delete conversations | conversationids[] | None | Remove conversation history |
| `core_message_get_conversations` | ✅ READ | Get user's conversations | userid | limitfrom, limitnum, type, favourites, mergeself | Returns conversation list |
| `core_message_get_conversation` | ✅ READ | Get single conversation | userid, conversationid | includecontactrequests, includeprivacyinfo, memberlimit, memberoffset, messagelimit, messageoffset, newestmessagesfirst | Detailed conversation view |
| `core_message_get_conversation_messages` | ✅ READ | Get messages in conversation | currentuserid, convid | limitfrom, limitnum, newest, timefrom | Paginated message history |
| `core_message_get_messages` | ✅ READ | Get messages | useridto, useridfrom | type, read, newestfirst, limitfrom, limitnum | Legacy message retrieval |
| `core_message_get_conversation_members` | ✅ READ | Get conversation members | userid, conversationid | limitfrom, limitnum, includependingrequests | List participants |
| `core_message_get_member_info` | ✅ READ | Get member information | referenceuserid, userids[] | includecontactrequests, includeprivacyinfo | User info in context |
| `core_message_get_unread_conversation_counts` | ✅ READ | Get unread counts | userid | None | Unread message counts |
| `core_message_get_unread_conversations_count` | ✅ READ | Get unread conversation count | userid | None | Total unread conversations |
| `core_message_mark_all_conversation_messages_as_read` | ⚠️ WRITE | Mark conversation as read | userid, conversationid | None | Clear unread status |
| `core_message_mark_all_messages_as_read` | ⚠️ WRITE | Mark all messages read | useridto | useridfrom | Mark all as read |
| `core_message_mark_all_notifications_as_read` | ⚠️ WRITE | Mark all notifications read | useridto | useridfrom | Clear notification badges |
| `core_message_mark_message_read` | ⚠️ WRITE | Mark single message read | messageid, timeread | None | Mark specific message |
| `core_message_block_user` | ⚠️ WRITE | Block a user | userid, blockeduserid | None | Block user from messaging |
| `core_message_unblock_user` | ⚠️ WRITE | Unblock a user | userid, unblockeduserid | None | Unblock user |
| `core_message_get_blocked_users` | ✅ READ | Get blocked users list | userid | None | Returns blocked user IDs |
| `core_message_data_for_messagearea_search_messages` | ✅ READ | Search messages | userid, search | limitfrom, limitnum | Search message content |
| `core_message_message_processor_config_form` | ✅ READ | Get processor config | userid, name | None | Notification settings |
| `core_message_get_user_notification_preferences` | ✅ READ | Get notification preferences | userid | None | User's notification settings |
| `core_message_set_favourite_conversations` | ⚠️ WRITE | Favorite conversations | userid, conversations[] | None | Mark conversations as favorites |
| `core_message_unset_favourite_conversations` | ⚠️ WRITE | Unfavorite conversations | userid, conversations[] | None | Remove from favorites |
| `core_message_create_contact_request` | ⚠️ WRITE | Send contact request | userid, requesteduserid | None | Request to add contact |
| `core_message_confirm_contact_request` | ⚠️ WRITE | Accept contact request | userid, requesteduserid | None | Approve contact request |
| `core_message_decline_contact_request` | ⚠️ WRITE | Decline contact request | userid, requesteduserid | None | Reject contact request |
| `core_message_get_contact_requests` | ✅ READ | Get contact requests | userid | limitfrom, limitnum | Pending contact requests |
| `core_message_get_user_contacts` | ✅ READ | Get user contacts | userid | limitfrom, limitnum | User's contact list |

---

## 6. CORE_COHORT Module - Cohort Management

### Cohort Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_cohort_create_cohorts` | ⚠️ WRITE | Create cohorts | cohorts[] (categorytype, name, idnumber) | description, descriptionformat, visible, theme | 🔑 Requires moodle/cohort:manage |
| `core_cohort_update_cohorts` | ⚠️ WRITE | Update cohorts | cohorts[] (id + fields) | name, idnumber, description, visible, theme | 🔑 Requires cohort_id |
| `core_cohort_delete_cohorts` | ⚠️ WRITE | Delete cohorts | cohortids[] | None | 🔑 DESTRUCTIVE operation |
| `core_cohort_get_cohorts` | ✅ READ | Get cohorts by ID | cohortids[] | None | Returns cohort details |
| `core_cohort_search_cohorts` | ✅ READ | Search cohorts | query, context[contextid/contextlevel] | includes, limitfrom, limitnum | Search by name/idnumber |
| `core_cohort_add_cohort_members` | ⚠️ WRITE | Add users to cohort | members[] (cohorttype, cohortid, userid) | None | 🔑 Requires cohort_id, user_ids |
| `core_cohort_delete_cohort_members` | ⚠️ WRITE | Remove users from cohort | members[] (cohortid, userid) | None | Remove cohort membership |
| `core_cohort_get_cohort_members` | ✅ READ | Get cohort members | cohortids[] | None | Returns user list per cohort |

---

## 7. CORE_GRADE Module - Grading System

### Grade Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_grades_get_grades` | ✅ READ | Get grades for users | courseid, component, activityid | userids[] | **DEPRECATED** - use core_grades_get_enrolled_users_for_search_widget |
| `core_grades_update_grades` | ⚠️ WRITE | Update activity grades | source, courseid, component, activityid, itemnumber, grades[], itemdetails[] | None | 🔑 Update gradebook items |
| `core_grades_create_gradecategories` | ⚠️ WRITE | Create grade categories | courseid, categories[] | None | Create grade category structure |
| `core_grades_grader_gradingpanel_point_fetch` | ✅ READ | Get grading panel data | component, contextid, itemname, gradeduserid | None | For advanced grading |
| `core_grades_grader_gradingpanel_point_store` | ⚠️ WRITE | Save grading panel data | component, contextid, itemname, gradeduserid, formdata | None | Store grading data |
| `gradereport_overview_get_course_grades` | ✅ READ | Get course grades overview | userid | None | User's grades across all courses |
| `gradereport_overview_view_grade_report` | ✅ READ | Log grade report view | courseid | userid | Trigger view event |
| `gradereport_user_get_grade_items` | ✅ READ | Get grade items | courseid | userid, groupid | Grade items in course |
| `gradereport_user_get_grades_table` | ✅ READ | Get grades table | courseid | userid, groupid | Full grade table data |
| `gradereport_user_view_grade_report` | ✅ READ | Log user grade report view | courseid | userid | Trigger report view event |
| `core_grades_get_enrolled_users_for_search_widget` | ✅ READ | Search enrolled users for grading | courseid | search, searchanywhere, page, perpage | Find users to grade |

---

## 8. CORE_GROUP Module - Group Management

### Group Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_group_create_groups` | ⚠️ WRITE | Create groups | groups[] (courseid, name) | description, descriptionformat, enrolmentkey, idnumber | 🔑 Requires course_id |
| `core_group_update_groups` | ⚠️ WRITE | Update groups | groups[] (id + fields) | name, description, enrolmentkey, idnumber | 🔑 Requires group_id |
| `core_group_delete_groups` | ⚠️ WRITE | Delete groups | groupids[] | None | 🔑 DESTRUCTIVE operation |
| `core_group_get_groups` | ✅ READ | Get groups by ID | groupids[] | None | Returns group details |
| `core_group_get_course_groups` | ✅ READ | Get all groups in course | courseid | None | Returns all course groups |
| `core_group_get_activity_allowed_groups` | ✅ READ | Get groups for activity | cmid | userid | Groups with access to module |
| `core_group_get_activity_groupmode` | ✅ READ | Get activity group mode | cmid | None | Returns: 0=none, 1=separate, 2=visible |
| `core_group_get_course_user_groups` | ✅ READ | Get user's groups in course | courseid | userid, groupingid | User's group memberships |
| `core_group_get_course_groupings` | ✅ READ | Get course groupings | courseid | None | Returns groupings (collections of groups) |
| `core_group_get_groupings` | ✅ READ | Get groupings by ID | groupingids[] | returngroups | Grouping details with optional groups |
| `core_group_get_group_members` | ✅ READ | Get group members | groupids[] | None | Returns user list per group |
| `core_group_add_group_members` | ⚠️ WRITE | Add users to groups | members[] (groupid, userid) | None | 🔑 Requires group_id, user_ids |
| `core_group_delete_group_members` | ⚠️ WRITE | Remove users from groups | members[] (groupid, userid) | None | Remove group membership |
| `core_group_create_groupings` | ⚠️ WRITE | Create groupings | groupings[] (courseid, name) | description, descriptionformat, idnumber | 🔑 Requires course_id |
| `core_group_update_groupings` | ⚠️ WRITE | Update groupings | groupings[] (id + fields) | name, description, idnumber | 🔑 Requires grouping_id |
| `core_group_delete_groupings` | ⚠️ WRITE | Delete groupings | groupingids[] | None | 🔑 DESTRUCTIVE operation |
| `core_group_assign_grouping` | ⚠️ WRITE | Assign group to grouping | assignments[] (groupingid, groupid) | None | Add group to grouping |
| `core_group_unassign_grouping` | ⚠️ WRITE | Remove group from grouping | unassignments[] (groupingid, groupid) | None | Remove from grouping |

---

## 9. CORE_COMPLETION Module - Activity Completion

### Completion Tracking

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_completion_get_activities_completion_status` | ✅ READ | Get completion status for activities | courseid, userid | None | Returns completion for all activities |
| `core_completion_get_course_completion_status` | ✅ READ | Get overall course completion | courseid, userid | None | Course completion percentage |
| `core_completion_mark_course_self_completed` | ⚠️ WRITE | Mark course as self-completed | courseid | None | User marks course complete |
| `core_completion_update_activity_completion_status_manually` | ⚠️ WRITE | Manually update activity completion | cmid, completed | None | 🔑 Requires manual completion enabled |
| `core_completion_override_activity_completion_status` | ⚠️ WRITE | Override completion status | userid, cmid, newstate | None | 🔑 Teacher override of completion |
| `core_completion_get_enrolled_users_by_completion` | ✅ READ | Get users by completion status | courseid | filters[] | Filter users by completion criteria |

---

## 10. CORE_NOTES Module - Notes

### Notes Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_notes_create_notes` | ⚠️ WRITE | Create user notes | notes[] (userid, publishstate, courseid, text) | subject, format | 🔑 publishstate: site, course, personal |
| `core_notes_delete_notes` | ⚠️ WRITE | Delete notes | notes[] (id) | None | 🔑 DESTRUCTIVE operation |
| `core_notes_get_notes` | ✅ READ | Get notes | courseid | userid | Returns notes for user in course |
| `core_notes_get_course_notes` | ✅ READ | Get all course notes | courseid | userid | All notes in course context |
| `core_notes_update_notes` | ⚠️ WRITE | Update notes | notes[] (id, publishstate, text) | subject, format | Modify existing notes |
| `core_notes_view_notes` | ✅ READ | Log notes view | courseid | userid | Trigger view event |

---

## 11. CORE_BADGES Module - Badges & Achievements

### Badge Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_badges_get_user_badges` | ✅ READ | Get user's badges | None (current user) | userid, courseid, page, perpage, search, onlypublic | Returns earned badges |
| `core_badges_get_user_badge_by_hash` | ✅ READ | Get badge by hash | hash | None | Retrieve badge by unique hash |

---

## 12. CORE_FILES Module - File Management

### File Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_files_get_files` | ✅ READ | Get files in context | contextid | component, filearea, itemid, filepath, filename, modified, contextlevel, instanceid | Returns file list |
| `core_files_upload` | ⚠️ WRITE | Upload file | contextid, component, filearea, itemid, filepath, filename, filecontent | contextlevel, instanceid | 🔑 Upload to file area |
| `core_files_delete_draft_files` | ⚠️ WRITE | Delete draft files | draftitemid, files[] | None | Remove files from draft area |

---

## 13. MOD_FORUM Module - Forum Discussions

### Forum Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `mod_forum_get_forums_by_courses` | ✅ READ | Get forums in courses | courseids[] | None | Returns forum list |
| `mod_forum_get_forum_discussions` | ✅ READ | Get forum discussions | forumid | sortorder, page, perpage, groupid | Returns discussion threads |
| `mod_forum_get_forum_discussion_posts` | ✅ READ | Get posts in discussion | discussionid | sortby, sortdirection | Returns post tree |
| `mod_forum_get_discussion_post` | ✅ READ | Get single post | postid | None | Detailed post information |
| `mod_forum_get_forum_discussions_paginated` | ✅ READ | Get paginated discussions | forumid | sortby, sortdirection, page, perpage | Legacy pagination |
| `mod_forum_view_forum` | ✅ READ | Log forum view | forumid | None | Trigger view event |
| `mod_forum_view_forum_discussion` | ✅ READ | Log discussion view | discussionid | None | Trigger discussion view |
| `mod_forum_add_discussion` | ⚠️ WRITE | Create new discussion | forumid, subject, message | options[] (discussionpinned, discussionsubscribe, etc.) | 🔑 Requires forum_id |
| `mod_forum_add_discussion_post` | ⚠️ WRITE | Reply to discussion | postid, subject, message | options[] (discussionsubscribe, private, etc.) | 🔑 Create reply post |
| `mod_forum_update_discussion_post` | ⚠️ WRITE | Edit post | postid | subject, message, options[] | Modify existing post |
| `mod_forum_can_add_discussion` | ✅ READ | Check if can post | forumid | groupid | Check posting permissions |
| `mod_forum_set_subscription_state` | ⚠️ WRITE | Subscribe/unsubscribe | forumid, discussionid, targetstate | None | targetstate: 0=unsubscribe, 1=subscribe |
| `mod_forum_set_lock_state` | ⚠️ WRITE | Lock/unlock discussion | forumid, discussionid, targetstate | None | 🔑 Requires permission |
| `mod_forum_toggle_favourite_state` | ⚠️ WRITE | Favorite/unfavorite discussion | discussionid, targetstate | None | Mark discussion as favorite |
| `mod_forum_set_pin_state` | ⚠️ WRITE | Pin/unpin discussion | discussionid, targetstate | None | 🔑 Pin to top of forum |
| `mod_forum_delete_post` | ⚠️ WRITE | Delete post | postid | None | 🔑 DESTRUCTIVE operation |

---

## 14. MOD_ASSIGN Module - Assignments

### Assignment Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `mod_assign_get_assignments` | ✅ READ | Get assignments in courses | courseids[] | capabilities[], includenotenrolledcourses | Returns assignment list |
| `mod_assign_get_submissions` | ✅ READ | Get assignment submissions | assignmentids[] | status, since, before | Returns submission details |
| `mod_assign_get_user_mappings` | ✅ READ | Get blind marking mappings | assignmentids[] | None | Returns anonymized user IDs |
| `mod_assign_get_grades` | ✅ READ | Get assignment grades | assignmentids[] | since | Returns grading information |
| `mod_assign_get_user_flags` | ✅ READ | Get user flags | assignmentids[] | None | Returns assignment flags |
| `mod_assign_set_user_flags` | ⚠️ WRITE | Set user flags | assignmentid, userflags[] | None | Set extension, workflow state |
| `mod_assign_get_participant` | ✅ READ | Get assignment participant | assignid, userid | embeduser | Participant details |
| `mod_assign_list_participants` | ✅ READ | List assignment participants | assignid | groupid, filter, skip, limit | Paginated participant list |
| `mod_assign_view_assign` | ✅ READ | Log assignment view | assignid | None | Trigger view event |
| `mod_assign_view_submission_status` | ✅ READ | Log submission status view | assignid | None | View submission status |
| `mod_assign_view_grading_table` | ✅ READ | Log grading table view | assignid | None | View grading interface |
| `mod_assign_view_grading_form` | ✅ READ | Log grading form view | assignid, userid | None | View single submission grade |
| `mod_assign_save_submission` | ⚠️ WRITE | Save draft submission | assignmentid, plugindata | None | 🔑 Save assignment submission |
| `mod_assign_submit_for_grading` | ⚠️ WRITE | Submit assignment | assignmentid | acceptsubmissionstatement | 🔑 Final submission |
| `mod_assign_save_grade` | ⚠️ WRITE | Save assignment grade | assignmentid, userid, grade, attemptnumber | advancedgradingdata, addattempt, workflowstate, applytoall | 🔑 Grade submission |
| `mod_assign_save_user_extensions` | ⚠️ WRITE | Grant submission extensions | assignmentid, userids[], dates[] | None | Extend due dates |
| `mod_assign_reveal_identities` | ⚠️ WRITE | Reveal blind marking identities | assignmentid | None | 🔑 End anonymous grading |
| `mod_assign_revert_submissions_to_draft` | ⚠️ WRITE | Revert to draft | assignmentid, userids[] | None | Unlock submissions |
| `mod_assign_lock_submissions` | ⚠️ WRITE | Lock submissions | assignmentid, userids[] | None | Prevent further edits |
| `mod_assign_unlock_submissions` | ⚠️ WRITE | Unlock submissions | assignmentid, userids[] | None | Allow editing |
| `mod_assign_save_grade_item` | ⚠️ WRITE | Update grade item | assignmentid, gradeitem | None | Modify grade settings |
| `mod_assign_copy_previous_attempt` | ⚠️ WRITE | Copy from previous attempt | assignmentid | None | Reuse previous submission |
| `mod_assign_start_submission` | ⚠️ WRITE | Start new submission attempt | assignmentid | None | Begin submission process |
| `mod_assign_submit_grading_form` | ⚠️ WRITE | Submit advanced grading | assignmentid, userid, jsonformdata | None | Submit rubric/guide grading |

---

## 15. MOD_QUIZ Module - Quizzes

### Quiz Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `mod_quiz_get_quizzes_by_courses` | ✅ READ | Get quizzes in courses | courseids[] | None | Returns quiz list |
| `mod_quiz_view_quiz` | ✅ READ | Log quiz view | quizid | None | Trigger view event |
| `mod_quiz_get_user_attempts` | ✅ READ | Get user's quiz attempts | quizid | userid, status, includepr previews | Returns attempt history |
| `mod_quiz_get_user_best_grade` | ✅ READ | Get user's best grade | quizid, userid | None | Best grade achieved |
| `mod_quiz_get_combined_review_options` | ✅ READ | Get review options | quizid | userid | What user can see in review |
| `mod_quiz_start_attempt` | ⚠️ WRITE | Start quiz attempt | quizid | preflightdata[], forcenew | 🔑 Begin quiz attempt |
| `mod_quiz_get_attempt_data` | ✅ READ | Get attempt question data | attemptid | page | Questions for attempt page |
| `mod_quiz_get_attempt_summary` | ✅ READ | Get attempt summary | attemptid | preflightdata[] | Attempt overview |
| `mod_quiz_get_attempt_review` | ✅ READ | Get attempt review | attemptid | page | Review completed attempt |
| `mod_quiz_view_attempt` | ✅ READ | Log attempt view | attemptid, page | None | Trigger attempt view |
| `mod_quiz_view_attempt_summary` | ✅ READ | Log summary view | attemptid | preflightdata[] | View summary page |
| `mod_quiz_view_attempt_review` | ✅ READ | Log review view | attemptid | None | View review page |
| `mod_quiz_get_quiz_feedback_for_grade` | ✅ READ | Get feedback for grade | quizid, grade | None | Feedback based on score |
| `mod_quiz_get_quiz_access_information` | ✅ READ | Get quiz access info | quizid | None | Access rules and restrictions |
| `mod_quiz_get_attempt_access_information` | ✅ READ | Get attempt access info | quizid | attemptid | Access info for attempt |
| `mod_quiz_get_quiz_required_qtypes` | ✅ READ | Get required question types | quizid | None | Question types in quiz |
| `mod_quiz_save_attempt` | ⚠️ WRITE | Save attempt answers | attemptid, data[] | preflightdata[] | 🔑 Save question responses |
| `mod_quiz_process_attempt` | ⚠️ WRITE | Submit quiz attempt | attemptid | data[], finishattempt, timeup, preflightdata[] | 🔑 Finalize attempt |
| `mod_quiz_re_add_question_usage_by_activity` | ⚠️ WRITE | Re-add question usage | attemptid | None | For question recovery |
| `mod_quiz_set_question_version` | ⚠️ WRITE | Set question version | slotid, newversion | None | Change question version |

---

## 16. MOD_LESSON Module - Lessons

### Lesson Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `mod_lesson_get_lessons_by_courses` | ✅ READ | Get lessons in courses | courseids[] | None | Returns lesson list |
| `mod_lesson_get_lesson_access_information` | ✅ READ | Get lesson access info | lessonid | None | Access restrictions |
| `mod_lesson_view_lesson` | ✅ READ | Log lesson view | lessonid | password | Trigger view event |
| `mod_lesson_get_questions_attempts` | ✅ READ | Get question attempts | lessonid | attempt, correct, pageid, userid | Returns attempt history |
| `mod_lesson_get_user_attempt` | ✅ READ | Get user attempt | lessonid, userid | lessonattempt | Single attempt details |
| `mod_lesson_get_user_attempt_grade` | ✅ READ | Get attempt grade | lessonid, lessonattempt | userid | Grade for attempt |
| `mod_lesson_get_content_pages_viewed` | ✅ READ | Get viewed pages | lessonid, lessonattempt | userid | Pages student viewed |
| `mod_lesson_get_user_timers` | ✅ READ | Get user timers | lessonid | userid | Lesson timer information |
| `mod_lesson_get_pages` | ✅ READ | Get lesson pages | lessonid | password | Page structure |
| `mod_lesson_launch_attempt` | ⚠️ WRITE | Start lesson attempt | lessonid | password, pageid, review | 🔑 Begin lesson |
| `mod_lesson_get_page_data` | ✅ READ | Get page data | lessonid, pageid | password, review, returncontents | Page content and options |
| `mod_lesson_process_page` | ⚠️ WRITE | Process page submission | lessonid, pageid, data[], password | review | 🔑 Submit page response |
| `mod_lesson_finish_attempt` | ⚠️ WRITE | Finish lesson attempt | lessonid | password, outoftime, review | 🔑 Complete lesson |

---

## 17. MOD_WORKSHOP Module - Peer Assessment

### Workshop Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `mod_workshop_get_workshops_by_courses` | ✅ READ | Get workshops in courses | courseids[] | None | Returns workshop list |
| `mod_workshop_get_workshop_access_information` | ✅ READ | Get workshop access info | workshopid | None | Access and phase info |
| `mod_workshop_view_workshop` | ✅ READ | Log workshop view | workshopid | None | Trigger view event |
| `mod_workshop_get_user_plan` | ✅ READ | Get workshop phase plan | workshopid | None | Phases and tasks |
| `mod_workshop_get_submission` | ✅ READ | Get submission | submissionid | None | Submission details |
| `mod_workshop_get_submissions` | ✅ READ | Get workshop submissions | workshopid | userid, groupid, page, perpage | Returns submissions list |
| `mod_workshop_view_submission` | ✅ READ | Log submission view | submissionid | None | Trigger submission view |
| `mod_workshop_add_submission` | ⚠️ WRITE | Create submission | workshopid, title, content | attachmentsid, contentformat | 🔑 Add workshop submission |
| `mod_workshop_update_submission` | ⚠️ WRITE | Update submission | submissionid | title, content, contentformat, attachmentsid | Modify submission |
| `mod_workshop_delete_submission` | ⚠️ WRITE | Delete submission | submissionid | None | 🔑 DESTRUCTIVE operation |
| `mod_workshop_get_assessment` | ✅ READ | Get assessment | assessmentid | None | Peer assessment details |
| `mod_workshop_get_reviewer_assessments` | ✅ READ | Get assessments by reviewer | workshopid | userid | Assessments user gave |
| `mod_workshop_get_submission_assessments` | ✅ READ | Get assessments for submission | submissionid | None | Assessments received |
| `mod_workshop_get_assessment_form_definition` | ✅ READ | Get assessment form | assessmentid | mode | Form structure for grading |
| `mod_workshop_update_assessment` | ⚠️ WRITE | Update assessment | assessmentid, data[] | None | 🔑 Save peer grading |
| `mod_workshop_evaluate_assessment` | ⚠️ WRITE | Evaluate assessment quality | assessmentid | grade, weight | 🔑 Grade the grader |
| `mod_workshop_evaluate_submission` | ⚠️ WRITE | Evaluate submission | submissionid, feedbacktext | published, gradeoverby, gradeover, feedbackformat, feedbackattachmentsid | 🔑 Teacher evaluation |

---

## 18. MOD_GLOSSARY Module - Glossary

### Glossary Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `mod_glossary_get_glossaries_by_courses` | ✅ READ | Get glossaries in courses | courseids[] | None | Returns glossary list |
| `mod_glossary_view_glossary` | ✅ READ | Log glossary view | id | mode | Trigger view event |
| `mod_glossary_view_entry` | ✅ READ | Log entry view | id | None | Trigger entry view |
| `mod_glossary_get_entries_by_letter` | ✅ READ | Get entries by letter | id, letter | from, limit, options[] | Browse alphabetically |
| `mod_glossary_get_entries_by_date` | ✅ READ | Get entries by date | id | order, from, limit, options[] | Browse by date |
| `mod_glossary_get_entries_by_category` | ✅ READ | Get entries by category | id, categoryid | from, limit, options[] | Browse by category |
| `mod_glossary_get_authors` | ✅ READ | Get entry authors | id | from, limit, options[] | List contributors |
| `mod_glossary_get_categories` | ✅ READ | Get glossary categories | id | from, limit | Category list |
| `mod_glossary_get_entries_to_approve` | ✅ READ | Get entries awaiting approval | id | letter, order, from, limit, options[] | Pending entries |
| `mod_glossary_get_entry_by_id` | ✅ READ | Get single entry | id | None | Entry details |
| `mod_glossary_add_entry` | ⚠️ WRITE | Add glossary entry | glossaryid, concept, definition | definitionformat, definitioninlinefiles, definitionoptions, attachments[], categories[] | 🔑 Create entry |
| `mod_glossary_update_entry` | ⚠️ WRITE | Update entry | entryid, concept, definition | definitionformat, definitioninlinefiles, definitionoptions, attachments[], categories[] | Modify entry |
| `mod_glossary_delete_entry` | ⚠️ WRITE | Delete entry | entryid | None | 🔑 DESTRUCTIVE operation |

---

## 19. MOD_WIKI Module - Wiki

### Wiki Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `mod_wiki_get_wikis_by_courses` | ✅ READ | Get wikis in courses | courseids[] | None | Returns wiki list |
| `mod_wiki_view_wiki` | ✅ READ | Log wiki view | wikiid | None | Trigger view event |
| `mod_wiki_view_page` | ✅ READ | Log page view | pageid | None | Trigger page view |
| `mod_wiki_get_subwikis` | ✅ READ | Get subwikis | wikiid | None | Returns subwiki list |
| `mod_wiki_get_subwiki_pages` | ✅ READ | Get subwiki pages | wikiid | groupid, userid, options[] | Returns page list |
| `mod_wiki_get_subwiki_files` | ✅ READ | Get subwiki files | wikiid | groupid, userid | Returns file list |
| `mod_wiki_get_page_contents` | ✅ READ | Get page content | pageid | None | Page content and metadata |
| `mod_wiki_get_page_for_editing` | ✅ READ | Get page for editing | pageid | section, lockonly | Editable page content |
| `mod_wiki_new_page` | ⚠️ WRITE | Create wiki page | title, content, wikiid | contentformat, subwikiid, userid, groupid | 🔑 Create new page |
| `mod_wiki_edit_page` | ⚠️ WRITE | Edit wiki page | pageid, content | section | 🔑 Modify page content |

---

## 20. MOD_FEEDBACK Module - Feedback/Survey

### Feedback Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `mod_feedback_get_feedbacks_by_courses` | ✅ READ | Get feedback activities | courseids[] | None | Returns feedback list |
| `mod_feedback_get_feedback_access_information` | ✅ READ | Get access info | feedbackid | courseid | Access restrictions |
| `mod_feedback_view_feedback` | ✅ READ | Log feedback view | feedbackid | moduleviewed, courseid | Trigger view event |
| `mod_feedback_get_current_completed_tmp` | ✅ READ | Get current incomplete response | feedbackid | None | Draft response |
| `mod_feedback_get_page_items` | ✅ READ | Get feedback items | feedbackid, page | None | Questions on page |
| `mod_feedback_launch_feedback` | ⚠️ WRITE | Start feedback | feedbackid | courseid | 🔑 Begin response |
| `mod_feedback_process_page` | ⚠️ WRITE | Submit feedback page | feedbackid, page, responses[] | goprevious, courseid | 🔑 Submit page responses |
| `mod_feedback_get_last_completed` | ✅ READ | Get completed feedback | feedbackid | None | User's last submission |
| `mod_feedback_get_analysis` | ✅ READ | Get feedback analysis | feedbackid | groupid, courseid | Analysis/statistics |
| `mod_feedback_get_unfinished_responses` | ✅ READ | Get incomplete responses | feedbackid | None | Draft responses list |
| `mod_feedback_get_finished_responses` | ✅ READ | Get completed responses | feedbackid | None | Submitted responses |
| `mod_feedback_get_non_respondents` | ✅ READ | Get users who haven't responded | feedbackid | groupid, sort, page, perpage | Non-respondent list |
| `mod_feedback_get_responses_analysis` | ✅ READ | Get response analysis | feedbackid | groupid, page, perpage | Detailed analysis |

---

## 21. MOD_CHAT Module - Chat Room

### Chat Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `mod_chat_get_chats_by_courses` | ✅ READ | Get chat rooms in courses | courseids[] | None | Returns chat list |
| `mod_chat_login_user` | ⚠️ WRITE | Login to chat | chatid | groupid | 🔑 Enter chat room |
| `mod_chat_get_chat_users` | ✅ READ | Get users in chat | chatsid | None | Current participants |
| `mod_chat_send_chat_message` | ⚠️ WRITE | Send chat message | chatsid, messagetext | beepid | 🔑 Post message |
| `mod_chat_get_chat_latest_messages` | ✅ READ | Get recent messages | chatsid, chatlasttime | None | Fetch new messages |
| `mod_chat_view_chat` | ✅ READ | Log chat view | chatid | None | Trigger view event |
| `mod_chat_get_sessions` | ✅ READ | Get chat sessions | chatid | groupid, showall | Past chat sessions |
| `mod_chat_get_session_messages` | ✅ READ | Get session messages | chatid, sessionstart | sessionend, groupid | Messages from session |

---

## 22. MOD_CHOICE Module - Choice/Poll

### Choice Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `mod_choice_get_choices_by_courses` | ✅ READ | Get choice activities | courseids[] | None | Returns choice list |
| `mod_choice_get_choice_options` | ✅ READ | Get choice options | choiceid | None | Available options |
| `mod_choice_get_choice_results` | ✅ READ | Get choice results | choiceid | None | Voting results |
| `mod_choice_view_choice` | ✅ READ | Log choice view | choiceid | None | Trigger view event |
| `mod_choice_submit_choice_response` | ⚠️ WRITE | Submit choice | choiceid, responses[] | None | 🔑 Vote on choice |
| `mod_choice_delete_choice_responses` | ⚠️ WRITE | Delete responses | choiceid, responses[] | None | 🔑 Remove votes |

---

## 23. MOD_DATA Module - Database Activity

### Database Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `mod_data_get_databases_by_courses` | ✅ READ | Get database activities | courseids[] | None | Returns database list |
| `mod_data_view_database` | ✅ READ | Log database view | databaseid | None | Trigger view event |
| `mod_data_get_data_access_information` | ✅ READ | Get access info | databaseid | None | Access and capabilities |
| `mod_data_get_entries` | ✅ READ | Get database entries | databaseid | groupid, returncontents, page, perpage, sort, order | Returns entries |
| `mod_data_get_entry` | ✅ READ | Get single entry | entryid | returncontents | Entry details |
| `mod_data_add_entry` | ⚠️ WRITE | Add database entry | databaseid, data[] | groupid | 🔑 Create entry |
| `mod_data_update_entry` | ⚠️ WRITE | Update entry | entryid, data[] | None | Modify entry |
| `mod_data_delete_entry` | ⚠️ WRITE | Delete entry | entryid | None | 🔑 DESTRUCTIVE operation |
| `mod_data_approve_entry` | ⚠️ WRITE | Approve entry | entryid | None | Approve pending entry |
| `mod_data_disapprove_entry` | ⚠️ WRITE | Disapprove entry | entryid | None | Reject entry |
| `mod_data_get_fields` | ✅ READ | Get database fields | databaseid | None | Field definitions |
| `mod_data_search_entries` | ✅ READ | Search entries | databaseid | groupid, returncontents, page, perpage, advsearch[] | Search database |

---

## 24. MOD_SURVEY Module - Survey

### Survey Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `mod_survey_get_surveys_by_courses` | ✅ READ | Get surveys in courses | courseids[] | None | Returns survey list |
| `mod_survey_view_survey` | ✅ READ | Log survey view | surveyid | None | Trigger view event |
| `mod_survey_get_questions` | ✅ READ | Get survey questions | surveyid | None | Question list |
| `mod_survey_submit_answers` | ⚠️ WRITE | Submit survey responses | surveyid, answers[] | None | 🔑 Submit survey |

---

## 25. MOD_H5PACTIVITY Module - H5P Interactive Content

### H5P Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `mod_h5pactivity_get_h5pactivities_by_courses` | ✅ READ | Get H5P activities | courseids[] | None | Returns H5P list |
| `mod_h5pactivity_view_h5pactivity` | ✅ READ | Log H5P view | h5pactivityid | None | Trigger view event |
| `mod_h5pactivity_get_attempts` | ✅ READ | Get user attempts | h5pactivityid | userids[] | Returns attempt list |
| `mod_h5pactivity_get_results` | ✅ READ | Get attempt results | h5pactivityid | attemptids[] | Attempt scores/data |
| `mod_h5pactivity_get_user_attempts` | ✅ READ | Get user's attempts | h5pactivityid | sortorder, page, perpage | Paginated attempts |
| `mod_h5pactivity_log_report_viewed` | ✅ READ | Log report view | h5pactivityid | userid, attemptid | Trigger report view |

---

## 26. CORE_REPORTBUILDER Module - Custom Reports

### Report Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_reportbuilder_retrieve_report` | ✅ READ | Retrieve custom report | reportid | page, perpage | Get report data |
| `core_reportbuilder_list_reports` | ✅ READ | List available reports | None | None | Returns report list |
| `core_reportbuilder_view_report` | ✅ READ | Log report view | reportid | None | Trigger view event |

---

## 27. GRADEREPORT Module - Grade Reports

### Grade Report Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `gradereport_overview_get_course_grades` | ✅ READ | Get grades overview | userid | None | All course grades |
| `gradereport_overview_view_grade_report` | ✅ READ | Log overview view | courseid | userid | Trigger report view |
| `gradereport_user_get_grade_items` | ✅ READ | Get grade items | courseid | userid, groupid | Grade items list |
| `gradereport_user_get_grades_table` | ✅ READ | Get full grades table | courseid | userid, groupid | Complete grade table |
| `gradereport_user_view_grade_report` | ✅ READ | Log user report view | courseid | userid | Trigger report view |
| `gradereport_singleview_get_grade_items_for_search_widget` | ✅ READ | Search grade items | courseid | None | For grade item picker |

---

## 28. CORE_QUESTION Module - Question Bank

### Question Bank Operations

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_question_get_random_question_summaries` | ✅ READ | Get random questions | categoryid, includesubcategories, tagids[], contextid | limit | Random question selection |
| `core_question_update_flag` | ⚠️ WRITE | Flag/unflag question | qubaid, questionid, qaid, slot, checksum, newstate | None | Mark question in attempt |
| `core_question_submit_tags_form` | ⚠️ WRITE | Submit question tags | questionid, contextid, formdata | None | Update question tags |

---

## Additional Core Modules

### CORE_WEBSERVICE - Web Service Management

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_webservice_get_site_info` | ✅ READ | Get site information | None | serviceshortnames | Returns site + user info |

### CORE_AUTH - Authentication

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_auth_confirm_user` | ⚠️ WRITE | Confirm user account | username, secret | None | Confirm email |
| `core_auth_request_password_reset` | ⚠️ WRITE | Request password reset | username, email | None | Trigger reset email |

### CORE_BLOCK - Block Management

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_block_get_course_blocks` | ✅ READ | Get course blocks | courseid | returncontents | Returns block list |
| `core_block_get_dashboard_blocks` | ✅ READ | Get dashboard blocks | None | returncontents, userid | User dashboard blocks |

### CORE_COMMENT - Comments

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_comment_get_comments` | ✅ READ | Get comments | contextlevel, instanceid, component, itemid, area | page | Returns comment list |
| `core_comment_add_comments` | ⚠️ WRITE | Add comment | comments[] (contextlevel, instanceid, component, itemid, area, content) | None | 🔑 Post comment |
| `core_comment_delete_comments` | ⚠️ WRITE | Delete comments | comments[] | None | 🔑 DESTRUCTIVE operation |

### CORE_TAG - Tagging System

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_tag_get_tags` | ✅ READ | Get tags | None | None | Returns tag list |
| `core_tag_get_tagindex` | ✅ READ | Get tag index | tagindex[] | from, ctx, rec, tag | Items with tag |
| `core_tag_get_tag_areas` | ✅ READ | Get tag areas | None | None | Taggable areas |
| `core_tag_get_tag_collections` | ✅ READ | Get tag collections | None | None | Tag collections |
| `core_tag_get_tag_cloud` | ✅ READ | Get tag cloud | tagcollid | None | Popular tags |
| `core_tag_update_tags` | ⚠️ WRITE | Update item tags | tags[] (id, name), contextid, component, itemtype, itemid | None | Tag items |

### CORE_CONTENTBANK - Content Bank

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_contentbank_delete_content` | ⚠️ WRITE | Delete content | contentid | None | 🔑 DESTRUCTIVE operation |
| `core_contentbank_rename_content` | ⚠️ WRITE | Rename content | contentid, name | None | Rename content item |
| `core_contentbank_set_content_visibility` | ⚠️ WRITE | Set visibility | contentid, visibility | None | Show/hide content |

### CORE_CUSTOMFIELD - Custom Fields

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_customfield_reload_template` | ✅ READ | Reload custom field template | component, area, itemid | None | Get custom field data |

### CORE_ROLE - Role Management

| Function | Category | Purpose | Required Parameters | Optional Parameters | Safety Notes |
|----------|----------|---------|---------------------|---------------------|--------------|
| `core_role_assign_roles` | ⚠️ WRITE | Assign roles to users | assignments[] (roleid, userid, contextid) | None | 🔑 Grant role permissions |
| `core_role_unassign_roles` | ⚠️ WRITE | Unassign roles | unassignments[] (roleid, userid, contextid) | None | 🔑 Remove role permissions |

---

## Summary Statistics

### By Module Type:

| Module Category | Function Count (Approx) | Read Functions | Write Functions |
|-----------------|-------------------------|----------------|-----------------|
| **CORE_COURSE** | 15 | 10 | 5 |
| **CORE_USER** | 15 | 8 | 7 |
| **CORE_ENROL** | 12 | 7 | 5 |
| **CORE_CALENDAR** | 14 | 9 | 5 |
| **CORE_MESSAGE** | 30+ | 15 | 15 |
| **CORE_COHORT** | 8 | 3 | 5 |
| **CORE_GRADE** | 10 | 8 | 2 |
| **CORE_GROUP** | 18 | 10 | 8 |
| **CORE_COMPLETION** | 6 | 4 | 2 |
| **CORE_NOTES** | 6 | 3 | 3 |
| **CORE_BADGES** | 2 | 2 | 0 |
| **CORE_FILES** | 3 | 1 | 2 |
| **MOD_FORUM** | 17 | 10 | 7 |
| **MOD_ASSIGN** | 25 | 12 | 13 |
| **MOD_QUIZ** | 20 | 14 | 6 |
| **MOD_LESSON** | 14 | 9 | 5 |
| **MOD_WORKSHOP** | 16 | 10 | 6 |
| **MOD_GLOSSARY** | 12 | 9 | 3 |
| **MOD_WIKI** | 10 | 7 | 3 |
| **MOD_FEEDBACK** | 14 | 11 | 3 |
| **MOD_CHAT** | 8 | 5 | 3 |
| **MOD_CHOICE** | 6 | 4 | 2 |
| **MOD_DATA** | 13 | 8 | 5 |
| **MOD_SURVEY** | 4 | 3 | 1 |
| **MOD_H5PACTIVITY** | 6 | 6 | 0 |
| **CORE_REPORTBUILDER** | 3 | 3 | 0 |
| **GRADEREPORT** | 6 | 6 | 0 |
| **CORE_QUESTION** | 3 | 1 | 2 |
| **Others** | 20+ | 15 | 5 |

### Total Estimated Functions: **300+**

---

## Implementation Priority Recommendations

### HIGH PRIORITY (Currently Implemented - READ ONLY)
✅ Core course functions
✅ Core user functions
✅ Core enrollment functions
✅ Core grade functions
✅ Assignment functions
✅ Calendar functions
✅ Message functions
✅ Forum functions
✅ Group functions

### MEDIUM PRIORITY (Missing READ functions)
- ⚠️ **MOD_QUIZ** - Quiz attempts, question data, reviews
- ⚠️ **MOD_LESSON** - Lesson pages, attempts, timers
- ⚠️ **MOD_WORKSHOP** - Submissions, assessments, peer reviews
- ⚠️ **MOD_GLOSSARY** - Entries, categories, browsing
- ⚠️ **MOD_WIKI** - Pages, subwikis, content
- ⚠️ **MOD_FEEDBACK** - Responses, analysis, non-respondents
- ⚠️ **MOD_DATA** - Entries, fields, search
- ⚠️ **CORE_COHORT** - Cohort details and membership
- ⚠️ **CORE_COMPLETION** - Completion tracking
- ⚠️ **CORE_NOTES** - User notes
- ⚠️ **CORE_BADGES** - Badge information

### LOW PRIORITY (Specialized)
- MOD_CHAT - Real-time chat
- MOD_CHOICE - Simple polls
- MOD_SURVEY - Surveys
- MOD_H5PACTIVITY - H5P content
- CORE_REPORTBUILDER - Custom reports
- CORE_TAG - Tagging system
- CORE_COMMENT - Comments
- CORE_BLOCK - Block management

### WRITE FUNCTIONS (Future Consideration)
All WRITE functions should be implemented ONLY after:
1. Comprehensive READ coverage is complete
2. Security model is fully designed
3. User permissions are properly validated
4. Audit logging is implemented
5. Rollback mechanisms are in place

---

## Safety Considerations

### Required for WRITE Operations:
1. **User Authentication** - Valid token with appropriate permissions
2. **Capability Checks** - Verify user has required capabilities
3. **Context Validation** - Ensure user has access to the context
4. **Input Sanitization** - Clean and validate all inputs
5. **Transaction Support** - Ability to rollback on errors
6. **Audit Logging** - Track all modifications
7. **Rate Limiting** - Prevent abuse
8. **Confirmation Prompts** - For destructive operations

### Course ID Requirements:
Many functions require `course_id` parameter:
- Always validate course exists
- Verify user enrollment/access
- Check course visibility
- Respect group restrictions

---

## Version Compatibility Notes

- Functions marked **DEPRECATED** should not be used
- `core_grades_get_grades` → Replaced with `core_grades_get_enrolled_users_for_search_widget`
- `core_user_get_users_by_id` → Replaced with `core_user_get_users_by_field`
- `enrol_manual_enrol_users` vs `core_enrol_submit_user_enrolment_form` - Different Moodle versions
- Always check your Moodle version's API documentation

---

## Data Sources

This audit compiled from:
- Official Moodle Developer Documentation (moodledev.io)
- MoodleDocs Web Services API pages (docs.moodle.org/dev/)
- Moodle GitHub repository (github.com/moodle/moodle)
- Moodle Web Services upgrade.txt files
- Moodle 4.5 Release Notes
- Community forums and blog posts
- Direct API inspection tools

**Last Updated:** 2025-01-26
**Moodle Versions Covered:** 3.8 - 4.5+

---

## Usage Notes

1. **Discovery**: Use `moodle_get_available_functions` to see what's enabled on your instance
2. **Testing**: Always test with READ functions first
3. **Permissions**: Many functions require specific capabilities
4. **Pagination**: Most list functions support limit/offset or page/perpage
5. **Error Handling**: All functions can throw exceptions - handle appropriately
6. **Rate Limits**: Respect Moodle's performance constraints
7. **Documentation**: Check `/admin/webservice/documentation.php` on your Moodle instance for exact parameters

