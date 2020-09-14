import {ReduxActionCreator, ReduxErrorActionCreator} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {ConferenceState} from "./reducer"

export const setFetchConferenceSuccess: ReduxActionCreator<ConferenceState> = conference => ({
  type: ActionType.FETCH_CONFERENCE_SUCCESS,
  payload: conference
})

export const setFetchConferenceError: ReduxErrorActionCreator<string> = (
  errorMessage: string
) => ({
  type: ActionType.FETCH_CONFERENCE_ERROR,
  payload: Error(errorMessage),
  error: true
})
