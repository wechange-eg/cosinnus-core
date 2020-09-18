import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchEventsError,
  setFetchEventsSuccess
} from "./actions"
import {EventJson} from "./models"
import {groupBySlots} from "../../utils/events"
import {Room} from "../conference/reducer"

/**
 * Fetch conference room (events and Rocket.Chat URL)
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchEvents: ReduxThunkActionCreator<[Room],
  Promise<void>> = (room: Room) => (dispatch: Dispatch) =>
  fetch(`/api/v2/conference-events/?room_id=${room.id}/`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: EventJson[]) => {
        dispatch(setFetchEventsSuccess(room.slug, groupBySlots(data)))
      })
    } else {
      dispatch(setFetchEventsError(room.slug, "Failed to fetch events"))
    }
  })
