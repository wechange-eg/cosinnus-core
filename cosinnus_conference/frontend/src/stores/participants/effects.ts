import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {Participant, ParticipantJson} from "./models"
import {setFetchParticipantsError, setFetchParticipantsSuccess} from "./actions"

/**
 * Fetch conference participants
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchParticipants: ReduxThunkActionCreator<[string], Promise<void>> = () => (
  dispatch: Dispatch) => {
  return fetch(`/api/v2/conferences/${window.conferenceId}/participants/?page_size=1000&limit=1000&`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: {results: ParticipantJson[]}) => {
        dispatch(setFetchParticipantsSuccess(data.results.map(json => Participant.fromJson(json))))
      })
    } else {
      dispatch(setFetchParticipantsError("Failed to fetch events"))
    }
  })
}
