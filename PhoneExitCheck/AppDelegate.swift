//
//  AppDelegate.swift
//  PhoneExitCheck
//
//  Created by Computer  on 08/05/26.
//

import Cocoa

@main
class AppDelegate: NSObject, NSApplicationDelegate {

    func applicationDidFinishLaunching(_ aNotification: Notification) {
        DeviceDataManager.shared.loadFromJSON()
        print("App launched and loaded device data")
    }

    func applicationWillTerminate(_ aNotification: Notification) {
    }

    func applicationSupportsSecureRestorableState(_ app: NSApplication) -> Bool {
        return true
    }


}