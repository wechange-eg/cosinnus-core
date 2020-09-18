import { ThunkAction } from "redux-thunk"
import { Action } from "redux"

import { RootState } from "../stores/rootReducer"

export interface ReduxActionCreator<P> {
  (arg0: P): {
    readonly type: string
    readonly payload: P
  }
}

export interface ReduxObjectActionCreator<P> {
  (...args: P): {
    readonly type: string
    readonly payload: {
      [K: string]: P[K]
    }
  }
}

export interface ReduxErrorActionCreator<P> {
  (arg0: P): {
    readonly type: string
    readonly payload: Error<P>
    readonly error: boolean
  }
}

export interface ReduxObjectErrorActionCreator<P> {
  (...args: P): {
    readonly type: string
    readonly payload: {
      [K: string]: Error<P>
    }
    readonly error: boolean
  }
}

export interface ReduxThunkActionCreator<P, R> {
  (...args: P): ThunkAction<R, RootState, void, Action>
}

export interface ReduxAsyncThunkActionCreator<P, R> {
  (...args: P): ThunkAction<R, RootState, void, Action>
}

export interface DispatchedReduxThunkActionCreator<R> {
  (...args: any): R
}
