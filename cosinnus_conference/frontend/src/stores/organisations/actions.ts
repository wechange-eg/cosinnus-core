import {ReduxActionCreator, ReduxErrorActionCreator} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {Organisation} from "./reducer"

export const setFetchOrganisationsSuccess: ReduxActionCreator<Organisation[]> = organisations => ({
  type: ActionType.FETCH_ORGANISATIONS_SUCCESS,
  payload: organisations
})

export const setFetchOrganisationsError: ReduxErrorActionCreator<string> = (
  errorMessage: string
) => ({
  type: ActionType.FETCH_ORGANISATIONS_ERROR,
  payload: Error(errorMessage),
  error: true
})
