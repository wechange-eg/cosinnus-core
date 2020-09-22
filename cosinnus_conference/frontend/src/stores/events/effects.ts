import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchEventsError,
  setFetchEventsSuccess
} from "./actions"
import {EventJson} from "./models"
import {groupBySlots} from "../../utils/events"
import {RootState} from "../rootReducer"

/**
 * Fetch conference events
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchEvents: ReduxThunkActionCreator<[boolean], Promise<void>> = (fetchAll) => (dispatch: Dispatch, getState: () => RootState) => {
  const state = getState()
  const roomId = state.room && state.room.props.id || 0
  let filterParam = ""
  if (!fetchAll) {
    filterParam = "room_id=" + roomId
  }
  return fetch(`/api/v2/conferences/${window.conferenceId}/events/?page_size=1000&${filterParam}`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: {results: EventJson[]}) => {
        dispatch(setFetchEventsSuccess(roomId, groupBySlots(data.results)))
      })
    } else {
      dispatch(setFetchEventsError(roomId, "Failed to fetch events"))
    }
  })
}
