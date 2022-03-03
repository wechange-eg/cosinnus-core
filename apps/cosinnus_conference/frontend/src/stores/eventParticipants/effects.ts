import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchEventParticipantsError,
  setFetchEventParticipantsLoading, setFetchEventParticipantsSuccess
} from "./actions"
import {RootState} from "../rootReducer"
import {EventParticipants} from "./reducer"

/**
 * Fetch conference event participant counts (from BBB)
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchEventParticipants: ReduxThunkActionCreator<[boolean], Promise<void>> = (fetchAll) => (
  dispatch: Dispatch, getState: () => RootState) => {
  const state = getState()
  const roomId = state.room && state.room.props.id.toString() || "0"
  dispatch(setFetchEventParticipantsLoading(roomId))
  let filterParam = ""
  if (!fetchAll) {
    filterParam = "room_id=" + roomId
  }
  return fetch(`/api/v2/conferences/${window.conferenceId}/event_participants/?page_size=1000&limit=1000&${filterParam}`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: {results: EventParticipants}) => {
        dispatch(setFetchEventParticipantsSuccess(roomId, data.results))
      })
    } else {
      dispatch(setFetchEventParticipantsError(roomId, "Failed to fetch events"))
    }
  })
}
