import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchConferenceError,
  setFetchConferenceSuccess,
} from "./actions"
import {resetRoom, setRoom} from "../room/actions"
import {Conference, ConferenceJson} from "./models"
import {Room} from "../room/models"
import {fetchParticipants} from "../participants/effects"

/**
 * Fetch conference data
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchConference: ReduxThunkActionCreator<[string],
  Promise<void>> = () => (dispatch: Dispatch) =>
  fetch(`/api/v2/conferences/${window.conferenceId}/`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: ConferenceJson) => {
        dispatch(setFetchConferenceSuccess(Conference.fromJson(data)))
        const room = data.rooms.find(room => room.id === window.conferenceRoomId)
        if (room) {
          dispatch(setRoom(Room.fromJson(room)))
        } else {
          dispatch(resetRoom())
        }
      })
    } else {
      dispatch(setFetchConferenceError("Failed to fetch translations"))
    }
  })
